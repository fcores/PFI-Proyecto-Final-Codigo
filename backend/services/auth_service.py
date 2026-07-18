import hashlib
import logging
import os
import secrets
from typing import Dict, Optional

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import HTTPException

from backend.models.auth import LoginResponse, UserInfo

load_dotenv()


class AuthService:
    """Autenticacion con soporte RBAC.

    Cuando hay base de datos disponible, los usuarios se leen de la tabla users.
    Sin base de datos, se usa el usuario unico de variables de entorno con rol administrador.
    """

    def __init__(self) -> None:
        """Inicializa el almacen de tokens y siembra usuarios iniciales si hay BD."""
        try:
            self._tokens: Dict[str, UserInfo] = {}
            self._seed_users()
        except Exception as exc:
            logger.error("Error al inicializar AuthService: %s", exc, exc_info=True)
            raise

    def _db_available(self) -> bool:
        """Verifica si la base de datos esta disponible."""
        try:
            from backend.db import is_db_available
            return is_db_available()
        except Exception:
            return False

    def _hash_password(self, password: str, salt: str) -> str:
        """Genera hash SHA-256 de la contrasena con salt."""
        try:
            salted = salt + password
            return hashlib.sha256(salted.encode("utf-8")).hexdigest()
        except Exception as exc:
            logger.error("Error al hashear contrasena: %s", exc, exc_info=True)
            raise

    def _seed_users(self) -> None:
        """Siembra usuarios iniciales en la BD si no existen."""
        try:
            if not self._db_available():
                return

            from backend.db import get_db, load_query
            queries = load_query("users.sql")

            seed_users = [
                ("admin", "admin123", "Administrador", "administrador"),
                ("prescriptor", "presc123", "Medico Prescriptor", "prescriptor"),
                ("auditor", "audit123", "Auditor Medico", "auditor"),
            ]

            with get_db() as conn:
                with conn.cursor() as cur:
                    for username, password, display_name, role in seed_users:
                        cur.execute(queries["find_user_by_username"], (username,))
                        if cur.fetchone() is None:
                            salt = secrets.token_hex(16)
                            password_hash = self._hash_password(password, salt)
                            cur.execute(
                                queries["insert_user"],
                                (username, password_hash, salt, display_name, role),
                            )
                            logger.info("Usuario '%s' creado con rol '%s'.", username, role)
        except Exception as exc:
            logger.error("Error al sembrar usuarios: %s", exc, exc_info=True)

    def _config(self):
        """Lee las credenciales desde variables de entorno (fallback sin BD)."""
        try:
            username = os.getenv("AUTH_USERNAME")
            password = os.getenv("AUTH_PASSWORD")
            display_name = os.getenv("AUTH_DISPLAY_NAME")
            return username, password, display_name
        except Exception as exc:
            logger.error("Error al leer config de auth: %s", exc, exc_info=True)
            raise

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
        """Autentica contra la base de datos."""
        try:
            from backend.db import get_db, load_query
            queries = load_query("users.sql")

            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["find_user_by_username"], (username,))
                    row = cur.fetchone()

            if row is None:
                raise HTTPException(status_code=401, detail="Usuario o contrasena incorrectos.")

            columns = ["id", "username", "password_hash", "salt", "display_name", "role", "active", "created_at"]
            user_data = dict(zip(columns, row))

            computed_hash = self._hash_password(password, user_data["salt"])
            if computed_hash != user_data["password_hash"]:
                raise HTTPException(status_code=401, detail="Usuario o contrasena incorrectos.")

            user = UserInfo(
                username=user_data["username"],
                display_name=user_data["display_name"],
                role=user_data["role"],
            )
            token = secrets.token_urlsafe(32)
            self._tokens[token] = user
            return LoginResponse(token=token, user=user)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error en login_db: %s", exc, exc_info=True)
            raise

    def _login_env(self, username: str, password: str) -> LoginResponse:
        """Autentica contra variables de entorno (fallback)."""
        try:
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
            self._tokens[token] = user
            return LoginResponse(token=token, user=user)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error en login_env: %s", exc, exc_info=True)
            raise

    def resolve(self, token: Optional[str]) -> UserInfo:
        """Resuelve un token de sesion a la informacion del usuario."""
        try:
            if not token or token not in self._tokens:
                raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")
            return self._tokens[token]
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error al resolver token: %s", exc, exc_info=True)
            raise

    def logout(self, token: Optional[str]) -> None:
        """Cierra la sesion invalidando el token."""
        try:
            if token and token in self._tokens:
                del self._tokens[token]
        except Exception as exc:
            logger.error("Error en logout: %s", exc, exc_info=True)
            raise
