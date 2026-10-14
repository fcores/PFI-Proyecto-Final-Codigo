"""Autenticacion con RBAC de 4 roles, Argon2id y sesiones persistentes.

- Passwords: Argon2id via backend.security.password, con migracion transparente
  desde el formato legacy SHA-256+salt (rehash en el proximo login exitoso).
- Sesiones: tabla auth_tokens en la RDS (token hasheado SHA-256 + expiracion),
  con cache en memoria de 60s para no golpear la base en cada request. Funciona
  con multiples replicas del backend.
- Sin base de datos (solo desarrollo local): fallback al usuario de variables
  de entorno con tokens en memoria del proceso.
- Revocacion: la sesion se resuelve contra la tabla users (rol y estado
  vigentes); al desactivar una cuenta, cambiarle el rol o su clave se borran
  sus tokens (invalidate_user).
- Fuerza bruta: tras _MAX_FAILED_ATTEMPTS fallos de un mismo usuario dentro de
  _LOCKOUT_WINDOW_SECONDS el login responde 429 hasta que vence la ventana.
"""

import hashlib
import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import HTTPException

from backend.models.auth import LoginResponse, UserInfo
from backend.security.password import hash_password, needs_rehash, verify_password

load_dotenv()

logger = logging.getLogger(__name__)

TOKEN_TTL_HOURS = 12
_CACHE_TTL_SECONDS = 60
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_WINDOW_SECONDS = 300

# Usuarios iniciales: (username, variable de entorno con la clave, clave de
# desarrollo, nombre visible, rol). En produccion la clave sale SOLO del
# entorno; si la variable no esta definida, ese usuario no se siembra.
_SEED_USERS = (
    ("superadmin", "APP_SUPERADMIN_PASSWORD", "super123", "Super Administrador", "super_admin"),
    ("admin", "APP_ADMIN_PASSWORD", "admin123", "Administrador", "administrador"),
    ("prescriptor", "APP_PRESCRIPTOR_PASSWORD", "presc123", "Medico Prescriptor", "prescriptor"),
    ("auditor", "APP_AUDITOR_PASSWORD", "audit123", "Auditor Medico", "auditor"),
)

_INVALID_CREDENTIALS = "Usuario o contrasena incorrectos."


class AuthService:
    """Autenticacion con soporte RBAC de 4 roles."""

    def __init__(self) -> None:
        """Inicializa el cache de sesiones y siembra usuarios iniciales si hay BD."""
        try:
            # Fallback sin BD (solo desarrollo local).
            self._tokens_mem: dict[str, UserInfo] = {}
            # Cache de sesiones con BD: token_hash -> (user, cached_until).
            self._cache: dict[str, tuple[UserInfo, float]] = {}
            # Intentos fallidos por usuario (timestamps) para el rate limit.
            self._failed: dict[str, deque] = defaultdict(deque)
            self._failed_lock = threading.Lock()
            # Hash de referencia para igualar el tiempo de respuesta cuando el
            # usuario no existe (evita enumerar cuentas por timing).
            self._dummy_hash, self._dummy_salt = hash_password(secrets.token_urlsafe(16))
            self._seed_users()
        except Exception as exc:
            logger.error("Error al inicializar AuthService: %s", exc, exc_info=True)
            raise

    def _db_available(self) -> bool:
        try:
            from backend.db import is_db_available

            return is_db_available()
        except Exception:
            return False

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _seed_users(self) -> None:
        """Siembra usuarios iniciales en la BD si no existen (Argon2id)."""
        try:
            if not self._db_available():
                return

            from backend.config import get_settings
            from backend.db import get_db, load_query

            queries = load_query("users.sql")
            is_production = get_settings().is_production

            with get_db() as conn:
                with conn.cursor() as cur:
                    for username, env_var, dev_password, display_name, role in _SEED_USERS:
                        cur.execute(queries["find_user_any_by_username"], (username,))
                        if cur.fetchone() is not None:
                            continue
                        password = os.getenv(env_var) or (None if is_production else dev_password)
                        if not password:
                            logger.warning(
                                "Usuario inicial '%s' no sembrado: definir %s para crearlo.",
                                username,
                                env_var,
                            )
                            continue
                        password_hash, salt = hash_password(password)
                        cur.execute(
                            queries["insert_user"],
                            (username, password_hash, salt, display_name, role),
                        )
                        logger.info("Usuario '%s' creado con rol '%s'.", username, role)
        except Exception as exc:
            logger.error("Error al sembrar usuarios: %s", exc, exc_info=True)

    def _config(self):
        """Credenciales desde variables de entorno (fallback sin BD)."""
        username = os.getenv("AUTH_USERNAME")
        password = os.getenv("AUTH_PASSWORD")
        display_name = os.getenv("AUTH_DISPLAY_NAME")
        return username, password, display_name

    # ── login ────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> LoginResponse:
        """Autentica al usuario y devuelve un token de sesion."""
        try:
            key = (username or "").strip().lower()
            self._check_lockout(key)
            try:
                if self._db_available():
                    response = self._login_db(username, password)
                else:
                    response = self._login_env(username, password)
            except HTTPException as exc:
                if exc.status_code == 401:
                    self._register_failure(key)
                raise
            self._clear_failures(key)
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error en login: %s", exc, exc_info=True)
            raise

    def _login_db(self, username: str, password: str) -> LoginResponse:
        from backend.db import get_db, load_query

        queries = load_query("users.sql")
        token_queries = load_query("auth_tokens.sql")

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["find_user_by_username"], (username,))
                columns = [desc[0] for desc in cur.description]
                row = cur.fetchone()

        if row is None:
            verify_password(password, self._dummy_hash, self._dummy_salt)
            raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS)

        user_data = dict(zip(columns, row))

        if not verify_password(password, user_data["password_hash"], user_data["salt"]):
            raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS)

        # Migracion transparente: rehash a Argon2id en el proximo login exitoso.
        if needs_rehash(user_data["password_hash"], user_data["salt"]):
            try:
                new_hash, new_salt = hash_password(password)
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["update_user_password_by_username"],
                            (new_hash, new_salt, username),
                        )
                logger.info("Password de '%s' migrada a Argon2id.", username)
            except Exception as exc:
                logger.error("No se pudo rehashear la password de '%s': %s", username, exc)

        user = UserInfo(
            username=user_data["username"],
            display_name=user_data["display_name"],
            role=user_data["role"],
        )

        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(token_queries["purge_expired_tokens"])
                cur.execute(
                    token_queries["insert_token"],
                    (token_hash, user.username, user.display_name, user.role, TOKEN_TTL_HOURS),
                )
        self._cache[token_hash] = (user, time.time() + _CACHE_TTL_SECONDS)
        return LoginResponse(token=token, user=user)

    def _login_env(self, username: str, password: str) -> LoginResponse:
        import hmac

        cfg_user, cfg_password, cfg_display = self._config()

        if not cfg_user or not cfg_password:
            raise HTTPException(
                status_code=503,
                detail="Autenticacion no configurada. Defini AUTH_USERNAME y AUTH_PASSWORD en el .env.",
            )

        valid_user = hmac.compare_digest(username, cfg_user)
        valid_password = hmac.compare_digest(password, cfg_password)
        if not (valid_user and valid_password):
            raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS)

        user = UserInfo(
            username=cfg_user,
            display_name=cfg_display or cfg_user,
            role="administrador",
        )
        token = secrets.token_urlsafe(32)
        self._tokens_mem[token] = user
        return LoginResponse(token=token, user=user)

    # ── resolucion de sesion ─────────────────────────────────────────────────

    def resolve(self, token: str | None) -> UserInfo:
        """Resuelve un token de sesion a la informacion del usuario."""
        try:
            if not token:
                raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")

            if not self._db_available():
                if token not in self._tokens_mem:
                    raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")
                return self._tokens_mem[token]

            token_hash = self._hash_token(token)

            cached = self._cache.get(token_hash)
            if cached and cached[1] > time.time():
                return cached[0]

            from backend.db import get_db, load_query

            token_queries = load_query("auth_tokens.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(token_queries["find_valid_token"], (token_hash,))
                    row = cur.fetchone()

            if row is None:
                self._cache.pop(token_hash, None)
                raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")

            user = UserInfo(username=row[0], display_name=row[1], role=row[2])
            self._cache[token_hash] = (user, time.time() + _CACHE_TTL_SECONDS)
            return user
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error al resolver token: %s", exc, exc_info=True)
            raise

    def logout(self, token: str | None) -> UserInfo | None:
        """Cierra la sesion invalidando el token. Es idempotente.

        Devuelve el usuario dueño de la sesion cerrada, o None si el token
        no existia o ya habia expirado.
        """
        try:
            if not token:
                logger.info("Logout sin token.")
                return None

            user = self._tokens_mem.pop(token, None)
            if self._db_available():
                token_hash = self._hash_token(token)
                cached = self._cache.pop(token_hash, None)
                if cached:
                    user = cached[0]

                from backend.db import get_db, load_query

                token_queries = load_query("auth_tokens.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        if user is None:
                            cur.execute(token_queries["find_valid_token"], (token_hash,))
                            row = cur.fetchone()
                            if row is not None:
                                user = UserInfo(username=row[0], display_name=row[1], role=row[2])
                        cur.execute(token_queries["delete_token"], (token_hash,))

            if user is None:
                logger.info("Logout con token inexistente o expirado.")
            else:
                logger.info("Sesion cerrada: usuario=%s rol=%s", user.username, user.role)
            return user
        except Exception as exc:
            logger.error("Error en logout: %s", exc, exc_info=True)
            raise

    # ── revocacion y cambio de clave ─────────────────────────────────────────

    def invalidate_user(self, username: str, keep_token: str | None = None) -> None:
        """Cierra todas las sesiones de un usuario (opcionalmente salvo una).

        Se invoca al desactivar la cuenta, cambiarle el rol o la clave. El cache
        de este proceso se limpia de inmediato; otras replicas lo hacen al
        vencer su TTL (_CACHE_TTL_SECONDS), porque resolve() vuelve a la base.
        """
        keep_hash = self._hash_token(keep_token) if keep_token else None
        for token, user in list(self._tokens_mem.items()):
            if user.username == username and token != keep_token:
                self._tokens_mem.pop(token, None)
        for token_hash, (user, _) in list(self._cache.items()):
            if user.username == username and token_hash != keep_hash:
                self._cache.pop(token_hash, None)

        if not self._db_available():
            return
        from backend.db import get_db, load_query

        token_queries = load_query("auth_tokens.sql")
        with get_db() as conn:
            with conn.cursor() as cur:
                if keep_hash:
                    cur.execute(token_queries["delete_other_tokens_by_username"], (username, keep_hash))
                else:
                    cur.execute(token_queries["delete_tokens_by_username"], (username,))
        logger.info("Sesiones de '%s' revocadas.", username)

    def change_own_password(self, token: str | None, current_password: str, new_password: str) -> None:
        """Cambia la clave del usuario de la sesion y cierra sus otras sesiones."""
        user = self.resolve(token)
        if not self._db_available():
            raise HTTPException(
                status_code=503,
                detail="El cambio de contrasena requiere base de datos.",
            )
        from backend.db import get_db, load_query

        queries = load_query("users.sql")
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["find_user_by_username"], (user.username,))
                columns = [desc[0] for desc in cur.description]
                row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")
        user_data = dict(zip(columns, row))
        if not verify_password(current_password, user_data["password_hash"], user_data["salt"]):
            raise HTTPException(status_code=400, detail="La contrasena actual no es correcta.")
        if current_password == new_password:
            raise HTTPException(status_code=400, detail="La nueva contrasena debe ser distinta de la actual.")

        new_hash, new_salt = hash_password(new_password)
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["update_user_password_by_username"], (new_hash, new_salt, user.username))
        self.invalidate_user(user.username, keep_token=token)
        logger.info("Password de '%s' cambiada por su titular.", user.username)

    # ── rate limit de login ──────────────────────────────────────────────────

    def _recent_failures(self, key: str, now: float) -> deque:
        attempts = self._failed[key]
        while attempts and now - attempts[0] > _LOCKOUT_WINDOW_SECONDS:
            attempts.popleft()
        return attempts

    def _check_lockout(self, key: str) -> None:
        now = time.time()
        with self._failed_lock:
            attempts = self._recent_failures(key, now)
            if len(attempts) >= _MAX_FAILED_ATTEMPTS:
                retry_in = int(_LOCKOUT_WINDOW_SECONDS - (now - attempts[0])) + 1
                minutes = max(1, (retry_in + 59) // 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Demasiados intentos fallidos. Proba de nuevo en {minutes} min.",
                    headers={"Retry-After": str(retry_in)},
                )

    def _register_failure(self, key: str) -> None:
        with self._failed_lock:
            self._recent_failures(key, time.time()).append(time.time())

    def _clear_failures(self, key: str) -> None:
        with self._failed_lock:
            self._failed.pop(key, None)
