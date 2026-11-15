"""Servicio de gestion de usuarios (ABM, solo super_admin)."""

import logging
import secrets
from collections.abc import Callable

from backend.error_handlers import ConflictError, DomainError, NotFoundError
from backend.models.auth import (
    PasswordResetRequest,
    UserAccount,
    UserCreateRequest,
    UserInfo,
    UserList,
    UserUpdateRequest,
)
from backend.repositories.user_repo import UserRepository
from backend.security.password import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """ABM de cuentas de usuario y asignacion de roles."""

    def __init__(
        self,
        repo: UserRepository,
        revoke_sessions: Callable[[str], None] | None = None,
        signing_service=None,
    ) -> None:
        """revoke_sessions(username) cierra las sesiones abiertas de una cuenta."""
        self._repo = repo
        self._revoke_sessions = revoke_sessions
        self._signing_service = signing_service

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

    def baja_propia(self, current_user: UserInfo, password: str) -> None:
        """Baja voluntaria de la propia cuenta con anonimizacion (RF-37).

        El username se conserva como seudonimo porque los asientos on-chain lo
        referencian; el nombre visible y la credencial se reemplazan, las
        sesiones se cierran y la clave de firma se revoca.
        """
        try:
            cuenta = self._repo.find_credentials(current_user.username)
            if cuenta is None:
                raise NotFoundError("Usuario no encontrado.")
            if not verify_password(password, cuenta["password_hash"], cuenta["salt"]):
                raise DomainError("La contraseña no es correcta.", status_code=400, error_type="validation_error")
            if cuenta["role"] == "super_admin" and self._repo.count_active_by_role("super_admin") <= 1:
                raise ConflictError("No se puede dar de baja al último administrador general activo.")

            hash_inutilizable, salt = hash_password(secrets.token_urlsafe(48))
            self._repo.anonymize(cuenta["id"], "Usuario dado de baja #%d" % cuenta["id"], hash_inutilizable, salt)
            self._revoke(cuenta["username"])
            if self._signing_service is not None:
                self._signing_service.revocar(cuenta["username"])
            logger.info("Cuenta '%s' dada de baja por su titular y anonimizada.", cuenta["username"])
        except DomainError:
            raise
        except Exception as exc:
            logger.error("Error en la baja voluntaria de %s: %s", current_user.username, exc, exc_info=True)
            raise

    def reset_password(self, user_id: int, data: PasswordResetRequest) -> None:
        """Reemplaza la password de una cuenta (Argon2id)."""
        target = self._repo.find_by_id(user_id)
        if target is None:
            raise NotFoundError("Usuario no encontrado.")
        password_hash, salt = hash_password(data.password)
        self._repo.update_password(user_id, password_hash, salt)
        self._revoke(target["username"])
        logger.info("Password de '%s' reseteada por un super admin.", target["username"])
