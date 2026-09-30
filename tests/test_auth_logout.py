"""Cierre de sesion: invalidacion del token e idempotencia (modo sin BD)."""

import pytest
from fastapi import HTTPException

from backend.services.auth_service import AuthService


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("AUTH_USERNAME", "tester")
    monkeypatch.setenv("AUTH_PASSWORD", "clave-test")
    monkeypatch.setenv("AUTH_DISPLAY_NAME", "Tester")
    monkeypatch.setattr(AuthService, "_db_available", lambda self: False)
    return AuthService()


def test_logout_invalida_el_token(svc):
    token = svc.login("tester", "clave-test").token
    assert svc.resolve(token).username == "tester"

    user = svc.logout(token)
    assert user is not None and user.username == "tester"

    with pytest.raises(HTTPException) as exc_info:
        svc.resolve(token)
    assert exc_info.value.status_code == 401


def test_logout_sin_token_o_desconocido_no_falla(svc):
    assert svc.logout(None) is None
    assert svc.logout("") is None
    assert svc.logout("token-inexistente") is None


def test_logout_es_idempotente(svc):
    token = svc.login("tester", "clave-test").token
    assert svc.logout(token) is not None
    assert svc.logout(token) is None


def test_logout_no_afecta_otras_sesiones(svc):
    token_a = svc.login("tester", "clave-test").token
    token_b = svc.login("tester", "clave-test").token

    svc.logout(token_a)

    assert svc.resolve(token_b).username == "tester"
