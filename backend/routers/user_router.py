"""Router de gestion de usuarios.

El ABM requiere super_admin; la baja voluntaria (RF-37) la pide cualquier
usuario autenticado sobre su propia cuenta.
"""

import logging

from fastapi import APIRouter, Header

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_user_service
from backend.models.auth import (
    PasswordResetRequest,
    UserAccount,
    UserCreateRequest,
    UserList,
    UserUpdateRequest,
)
from backend.models.suppression import SelfDeletionRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserList)
def list_users(authorization: str | None = Header(default=None)):
    """Lista todas las cuentas de usuario."""
    user = require_auth(authorization)
    require_role(user, ["super_admin"])
    return get_user_service().list()


@router.post("", response_model=UserAccount, status_code=201)
def create_user(
    data: UserCreateRequest,
    authorization: str | None = Header(default=None),
):
    """Crea una cuenta nueva con su rol."""
    user = require_auth(authorization)
    require_role(user, ["super_admin"])
    return get_user_service().create(data)


@router.put("/{user_id}", response_model=UserAccount)
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    authorization: str | None = Header(default=None),
):
    """Actualiza nombre visible, rol y estado activo de una cuenta."""
    user = require_auth(authorization)
    require_role(user, ["super_admin"])
    return get_user_service().update(user_id, data, user)


@router.post("/{user_id}/password")
def reset_password(
    user_id: int,
    data: PasswordResetRequest,
    authorization: str | None = Header(default=None),
):
    """Resetea la password de una cuenta."""
    user = require_auth(authorization)
    require_role(user, ["super_admin"])
    get_user_service().reset_password(user_id, data)
    return {"ok": True}


def baja_propia(
    data: SelfDeletionRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    """Da de baja y anonimiza la cuenta del usuario autenticado (RF-37)."""
    try:
        user = require_auth(authorization)
        get_user_service().baja_propia(user, data.password)
        return {"ok": True}
    except Exception as exc:
        logger.warning("Baja voluntaria no completada: %s", exc)
        raise


router.add_api_route("/me/baja", baja_propia, methods=["POST"])
