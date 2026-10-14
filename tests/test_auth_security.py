"""Rate limit de login, revocacion de sesiones y formato de errores de dominio."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.error_handlers import ConflictError, DomainError, install_error_handlers
from backend.services import auth_service as auth_module
from backend.services.auth_service import AuthService


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("AUTH_USERNAME", "tester")
    monkeypatch.setenv("AUTH_PASSWORD", "clave-test")
    monkeypatch.setenv("AUTH_DISPLAY_NAME", "Tester")
    monkeypatch.setattr(AuthService, "_db_available", lambda self: False)
    return AuthService()


def _login_fallido(svc):
    with pytest.raises(HTTPException) as exc_info:
        svc.login("tester", "incorrecta")
    return exc_info.value.status_code


def test_bloquea_tras_cinco_intentos_fallidos(svc):
    for _ in range(auth_module._MAX_FAILED_ATTEMPTS):
        assert _login_fallido(svc) == 401

    # Ni siquiera la clave correcta entra mientras dura el bloqueo.
    with pytest.raises(HTTPException) as exc_info:
        svc.login("tester", "clave-test")
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_el_bloqueo_vence_con_la_ventana(svc, monkeypatch):
    for _ in range(auth_module._MAX_FAILED_ATTEMPTS):
        _login_fallido(svc)

    real_time = auth_module.time.time
    monkeypatch.setattr(
        auth_module.time,
        "time",
        lambda: real_time() + auth_module._LOCKOUT_WINDOW_SECONDS + 1,
    )
    assert svc.login("tester", "clave-test").token


def test_un_login_exitoso_reinicia_el_contador(svc):
    for _ in range(auth_module._MAX_FAILED_ATTEMPTS - 1):
        _login_fallido(svc)
    svc.login("tester", "clave-test")
    for _ in range(auth_module._MAX_FAILED_ATTEMPTS - 1):
        assert _login_fallido(svc) == 401


def test_invalidate_user_cierra_todas_las_sesiones(svc):
    token_a = svc.login("tester", "clave-test").token
    token_b = svc.login("tester", "clave-test").token

    svc.invalidate_user("tester")

    for token in (token_a, token_b):
        with pytest.raises(HTTPException) as exc_info:
            svc.resolve(token)
        assert exc_info.value.status_code == 401


def test_invalidate_user_puede_conservar_la_sesion_actual(svc):
    token_a = svc.login("tester", "clave-test").token
    token_b = svc.login("tester", "clave-test").token

    svc.invalidate_user("tester", keep_token=token_a)

    assert svc.resolve(token_a).username == "tester"
    with pytest.raises(HTTPException):
        svc.resolve(token_b)


def _app_con_errores():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/dominio")
    def dominio():
        raise DomainError("Falta la justificacion_costo", status_code=422, error_type="validation_error")

    @app.get("/conflicto")
    def conflicto():
        raise ConflictError("Ya existe un paciente con esos datos.")

    return TestClient(app)


def test_domain_error_expone_detail_para_el_frontend():
    body = _app_con_errores().get("/dominio").json()
    assert body["status"] == 422
    assert body["detail"] == "Falta la justificacion_costo"
    assert body["title"] == body["detail"]


def test_conflict_error_expone_detail():
    resp = _app_con_errores().get("/conflicto")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Ya existe un paciente con esos datos."


def test_fabric_unavailable_no_filtra_detalles_internos():
    from backend.blockchain.fabric_client import FabricUnavailableError

    app = FastAPI()
    install_error_handlers(app)

    @app.get("/caido")
    def caido():
        raise FabricUnavailableError("urlopen error [Errno 111] 10.0.3.7:8081 peer0.prescriptor")

    body = TestClient(app).get("/caido").json()
    assert "10.0.3.7" not in body["detail"]
    assert "peer0" not in body["detail"]
