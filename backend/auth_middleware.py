import logging
from typing import List, Optional

from fastapi import HTTPException

from backend.dependencies import get_auth_service
from backend.models.auth import UserInfo

logger = logging.getLogger(__name__)


def extract_token(authorization: Optional[str]) -> Optional[str]:
    """Extrae el token Bearer del header Authorization."""
    try:
        if not authorization:
            return None
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()
    except Exception as exc:
        logger.error("Error al extraer token: %s", exc, exc_info=True)
        raise


def require_auth(authorization: Optional[str]) -> UserInfo:
    """Valida el token y devuelve la informacion del usuario autenticado."""
    try:
        token = extract_token(authorization)
        svc = get_auth_service()
        return svc.resolve(token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error en require_auth: %s", exc, exc_info=True)
        raise


def require_role(user: UserInfo, allowed_roles: List[str]) -> None:
    """Verifica que el usuario tenga uno de los roles permitidos."""
    try:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="No tenes permisos para realizar esta accion.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error en require_role: %s", exc, exc_info=True)
        raise
