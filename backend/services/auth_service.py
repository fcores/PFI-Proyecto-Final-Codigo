"""Autenticacion con RBAC de 4 roles, Argon2id y sesiones persistentes.

- Passwords: Argon2id via backend.security.password, con migracion transparente
  desde el formato legacy SHA-256+salt (rehash en el proximo login exitoso).
- Sesiones: tabla auth_tokens en la RDS (token hasheado SHA-256 + expiracion),
  con cache en memoria de 60s para no golpear la base en cada request. Funciona
  con multiples replicas del backend.
- Sin base de datos (solo desarrollo local): fallback al usuario de variables
  de entorno con tokens en memoria del proceso.
"""

import hashlib
import logging
import os
import secrets
import time

from dotenv import load_dotenv
from fastapi import HTTPException

from backend.models.auth import LoginResponse, UserInfo
from backend.security.password import hash_password, needs_rehash, verify_password

load_dotenv()

logger = logging.getLogger(__name__)

TOKEN_TTL_HOURS = 12
_CACHE_TTL_SECONDS = 60


class AuthService:
    """Autenticacion con soporte RBAC de 4 roles."""

    def __init__(self) -> None:
        """Inicializa el cache de sesiones y siembra usuarios iniciales si hay BD."""
        try:
            # Fallback sin BD (solo desarrollo local).
            self._tokens_mem: dict[str, UserInfo] = {}
            # Cache de sesiones con BD: token_hash -> (user, cached_until).
            self._cache: dict[str, tuple[UserInfo, float]] = {}
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

            from backend.db import get_db, load_query

            queries = load_query("users.sql")

            seed_users = [
                ("superadmin", "super123", "Super Administrador", "super_admin"),
                ("admin", "admin123", "Administrador", "administrador"),
                ("prescriptor", "presc123", "Medico Prescriptor", "prescriptor"),
                ("auditor", "audit123", "Auditor Medico", "auditor"),
            ]

            with get_db() as conn:
                with conn.cursor() as cur:
                    for username, password, display_name, role in seed_users:
                        cur.execute(queries["find_user_any_by_username"], (username,))
                        if cur.fetchone() is None:
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
            if self._db_available():
                return self._login_db(username, password)
            return self._login_env(username, password)
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
            raise HTTPException(status_code=401, detail="Usuario o contrasena incorrectos.")

        user_data = dict(zip(columns, row))

        if not verify_password(password, user_data["password_hash"], user_data["salt"]):
            raise HTTPException(status_code=401, detail="Usuario o contrasena incorrectos.")

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
            raise HTTPException(status_code=401, detail="Usuario o contrasena incorrectos.")

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

    def logout(self, token: str | None) -> None:
        """Cierra la sesion invalidando el token."""
        try:
            if not token:
                return
            self._tokens_mem.pop(token, None)
            if self._db_available():
                token_hash = self._hash_token(token)
                self._cache.pop(token_hash, None)

                from backend.db import get_db, load_query

                token_queries = load_query("auth_tokens.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(token_queries["delete_token"], (token_hash,))
        except Exception as exc:
            logger.error("Error en logout: %s", exc, exc_info=True)
            raise
