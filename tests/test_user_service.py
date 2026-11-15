"""Reglas del ABM de usuarios (UserService) con un repo fake en memoria."""

from datetime import datetime

import pytest

from backend.error_handlers import ConflictError, NotFoundError
from backend.models.auth import (
    PasswordResetRequest,
    UserCreateRequest,
    UserInfo,
    UserUpdateRequest,
)
from backend.security.password import verify_password
from backend.services.user_service import UserService


class FakeUserRepository:
    """Repo de usuarios en memoria con la misma interfaz que UserRepository."""

    def __init__(self):
        self._rows: dict[int, dict] = {}
        self._next_id = 1

    def list(self):
        return [dict(r) for r in self._rows.values()]

    def find_by_id(self, user_id):
        row = self._rows.get(user_id)
        return dict(row) if row else None

    def create(self, username, password_hash, salt, display_name, role):
        if any(r["username"] == username for r in self._rows.values()):
            raise ConflictError(f"El usuario '{username}' ya existe.")
        row = {
            "id": self._next_id,
            "username": username,
            "display_name": display_name,
            "role": role,
            "active": True,
            "created_at": datetime(2026, 1, 1),
            "password_hash": password_hash,
            "salt": salt,
        }
        self._rows[self._next_id] = row
        self._next_id += 1
        return {k: v for k, v in row.items() if k not in ("password_hash", "salt")}

    def update_profile(self, user_id, display_name, role, active):
        row = self._rows.get(user_id)
        if row is None:
            return False
        row.update(display_name=display_name, role=role, active=active)
        return True

    def update_password(self, user_id, password_hash, salt):
        row = self._rows.get(user_id)
        if row is None:
            return False
        row.update(password_hash=password_hash, salt=salt)
        return True


@pytest.fixture()
def repo():
    return FakeUserRepository()


@pytest.fixture()
def svc(repo):
    return UserService(repo)


@pytest.fixture()
def super_admin(svc):
    return svc.create(
        UserCreateRequest(
            username="root",
            password="superclave1",
            display_name="Root",
            role="super_admin",
        )
    )


def test_crear_usuario_con_rol(svc):
    cuenta = svc.create(
        UserCreateRequest(
            username="medico1",
            password="clave-larga-1",
            display_name="Dra. Perez",
            role="prescriptor",
        )
    )
    assert cuenta.role == "prescriptor"
    assert cuenta.active


def test_username_duplicado_da_conflicto(svc):
    req = UserCreateRequest(username="medico1", password="clave-larga-1", display_name="X", role="auditor")
    svc.create(req)
    with pytest.raises(ConflictError):
        svc.create(req)


def test_password_se_guarda_con_argon2(svc, repo):
    svc.create(UserCreateRequest(username="medico1", password="clave-larga-1", display_name="X", role="prescriptor"))
    row = repo._rows[1]
    assert row["salt"] == "argon2"
    assert verify_password("clave-larga-1", row["password_hash"], row["salt"])


def test_actualizar_rol_y_desactivar_a_otro(svc, super_admin):
    cuenta = svc.create(
        UserCreateRequest(username="medico1", password="clave-larga-1", display_name="X", role="prescriptor")
    )
    actual = UserInfo(username="root", display_name="Root", role="super_admin")
    actualizada = svc.update(
        cuenta.id,
        UserUpdateRequest(display_name="X", role="auditor", active=False),
        actual,
    )
    assert actualizada.role == "auditor"
    assert not actualizada.active


def test_super_admin_no_puede_desactivarse(svc, super_admin):
    actual = UserInfo(username="root", display_name="Root", role="super_admin")
    with pytest.raises(ConflictError):
        svc.update(
            super_admin.id,
            UserUpdateRequest(display_name="Root", role="super_admin", active=False),
            actual,
        )


def test_super_admin_no_puede_cambiarse_el_rol(svc, super_admin):
    actual = UserInfo(username="root", display_name="Root", role="super_admin")
    with pytest.raises(ConflictError):
        svc.update(
            super_admin.id,
            UserUpdateRequest(display_name="Root", role="auditor", active=True),
            actual,
        )


def test_actualizar_inexistente_da_not_found(svc):
    actual = UserInfo(username="root", display_name="Root", role="super_admin")
    with pytest.raises(NotFoundError):
        svc.update(999, UserUpdateRequest(display_name="X", role="auditor", active=True), actual)


def test_reset_password(svc, repo):
    cuenta = svc.create(
        UserCreateRequest(username="medico1", password="clave-larga-1", display_name="X", role="prescriptor")
    )
    svc.reset_password(cuenta.id, PasswordResetRequest(password="clave-nueva-9"))
    row = repo._rows[cuenta.id]
    assert verify_password("clave-nueva-9", row["password_hash"], row["salt"])
    assert not verify_password("clave-larga-1", row["password_hash"], row["salt"])


@pytest.fixture()
def revocadas():
    return []


@pytest.fixture()
def svc_revoca(repo, revocadas):
    return UserService(repo, revoke_sessions=revocadas.append)


def _cuenta(svc_revoca, username="medico1", role="prescriptor"):
    return svc_revoca.create(
        UserCreateRequest(username=username, password="clave-segura", display_name="Medico", role=role)
    )


def test_desactivar_cierra_las_sesiones(svc_revoca, revocadas, super_admin):
    cuenta = _cuenta(svc_revoca)
    svc_revoca.update(
        cuenta.id,
        UserUpdateRequest(display_name="Medico", role="prescriptor", active=False),
        UserInfo(username="root", display_name="Root", role="super_admin"),
    )
    assert revocadas == ["medico1"]


def test_cambiar_el_rol_cierra_las_sesiones(svc_revoca, revocadas, super_admin):
    cuenta = _cuenta(svc_revoca)
    svc_revoca.update(
        cuenta.id,
        UserUpdateRequest(display_name="Medico", role="auditor", active=True),
        UserInfo(username="root", display_name="Root", role="super_admin"),
    )
    assert revocadas == ["medico1"]


def test_editar_solo_el_nombre_no_cierra_sesiones(svc_revoca, revocadas, super_admin):
    cuenta = _cuenta(svc_revoca)
    svc_revoca.update(
        cuenta.id,
        UserUpdateRequest(display_name="Dr. Medico", role="prescriptor", active=True),
        UserInfo(username="root", display_name="Root", role="super_admin"),
    )
    assert revocadas == []


def test_resetear_la_clave_cierra_las_sesiones(svc_revoca, revocadas):
    cuenta = _cuenta(svc_revoca)
    svc_revoca.reset_password(cuenta.id, PasswordResetRequest(password="otra-clave-1"))
    assert revocadas == ["medico1"]
