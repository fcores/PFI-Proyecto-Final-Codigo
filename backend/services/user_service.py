"""Servicio de gestion de usuarios (ABM, solo super_admin)."""

import logging
from collections.abc import Callable

from backend.error_handlers import ConflictError, NotFoundError
from backend.models.auth import (
    PasswordResetRequest,
    UserAccount,
    UserCreateRequest,
    UserInfo,
    UserList,
    UserUpdateRequest,
)
from backend.repositories.user_repo import UserRepository
from backend.security.password import hash_password

logger = logging.getLogger(__name__)


class UserService:
    """ABM de cuentas de usuario y asignacion de roles."""

    def __init__(self, repo: UserRepository, revoke_sessions: Callable[[str], None] | None = None) -> None:
        """revoke_sessions(username) cierra las sesiones abiertas de una cuenta."""
        self._repo = repo
        self._revoke_sessions = revoke_sessions

    def _revoke(self, username: str) -> None:
        if self._revoke_sessions is not None:
            self._revoke_sessions(username)

    def list(self) -> UserList:
        """Lista todas las cuentas."""
        return UserList(users=[UserAccount(**row) for row in self._repo.list()])

    def create(self, data: UserCreateRequest) -> UserAccount:
        """Crea una cuenta nueva con password Argon2id."""
        password_hash, salt = hash_password(data.password)
        created = self._repo.create(
            data.username,
            password_hash,
            salt,
            data.display_name,
            data.role,
        )
        logger.info("Usuario '%s' creado con rol '%s'.", data.username, data.role)
        return UserAccount(**created)

    def update(self, user_id: int, data: UserUpdateRequest, current_user: UserInfo) -> UserAccount:
        """Actualiza display_name, rol y estado activo de una cuenta.

        Salvaguardas: un super_admin no puede desactivarse ni cambiarse el rol
        a si mismo (evita quedarse sin acceso a la gestion de usuarios).
        """
        target = self._repo.find_by_id(user_id)
        if target is None:
            raise NotFoundError("Usuario no encontrado.")

        if target["username"] == current_user.username:
            if not data.active:
                raise ConflictError("No podes desactivar tu propia cuenta.")
            if data.role != current_user.role:
                raise ConflictError("No podes cambiar tu propio rol.")

        self._repo.update_profile(user_id, data.display_name, data.role, data.active)
        # Una baja o un cambio de rol no pueden esperar a que expire el token.
        if not data.active or data.role != target["role"]:
            self._revoke(target["username"])
        updated = self._repo.find_by_id(user_id)
        return UserAccount(**updated)

    def reset_password(self, user_id: int, data: PasswordResetRequest) -> None:
        """Reemplaza la password de una cuenta (Argon2id)."""
        target = self._repo.find_by_id(user_id)
        if target is None:
            raise NotFoundError("Usuario no encontrado.")
        password_hash, salt = hash_password(data.password)
        self._repo.update_password(user_id, password_hash, salt)
        self._revoke(target["username"])
        logger.info("Password de '%s' reseteada por un super admin.", target["username"])
