import hmac
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
    """Autenticación simple para el prototipo.

    Las credenciales se leen exclusivamente desde variables de entorno (.env).
    Los tokens de sesión son opacos y se mantienen en memoria (se pierden al reiniciar).
    """

    def __init__(self) -> None:
        """Inicializa el almacén de tokens en memoria."""
        try:
            self._tokens: Dict[str, UserInfo] = {}
        except Exception as exc:
            logger.error("Error al inicializar AuthService: %s", exc, exc_info=True)
            raise

    def _config(self):
        """Lee las credenciales desde variables de entorno."""
        try:
            username = os.getenv("AUTH_USERNAME")
            password = os.getenv("AUTH_PASSWORD")
            display_name = os.getenv("AUTH_DISPLAY_NAME")
            return username, password, display_name
        except Exception as exc:
            logger.error("Error al leer config de auth: %s", exc, exc_info=True)
            raise

    def login(self, username: str, password: str) -> LoginResponse:
        cfg_user, cfg_password, cfg_display = self._config()

        if not cfg_user or not cfg_password:
            raise HTTPException(
                status_code=503,
                detail="Autenticación no configurada. Definí AUTH_USERNAME y AUTH_PASSWORD en el .env.",
            )

        valid_user = hmac.compare_digest(username, cfg_user)
        valid_password = hmac.compare_digest(password, cfg_password)
        if not (valid_user and valid_password):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

        user = UserInfo(username=cfg_user, display_name=cfg_display or cfg_user)
        token = secrets.token_urlsafe(32)
        self._tokens[token] = user
        return LoginResponse(token=token, user=user)

    def resolve(self, token: Optional[str]) -> UserInfo:
        if not token or token not in self._tokens:
            raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
        return self._tokens[token]

    def logout(self, token: Optional[str]) -> None:
        if token and token in self._tokens:
            del self._tokens[token]
