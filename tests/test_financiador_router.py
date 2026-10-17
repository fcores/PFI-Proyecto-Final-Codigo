"""Endpoints del panel del financiador: permisos por rol y respuesta (RF-40)."""

import importlib

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.error_handlers import install_error_handlers
from backend.models.auth import UserInfo
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import build_canonical_payload
from backend.services.financiador_service import FinanciadorService
from tests.fakes.fake_fabric_gateway import FakeFabricClient

# backend.routers reexporta el objeto router con el mismo nombre que el modulo.
modulo = importlib.import_module("backend.routers.financiador_router")
modulo_prescripciones = importlib.import_module("backend.routers.prescription_router")

_USUARIOS = {
    "Bearer fin": UserInfo(username="fin", display_name="Prepaga", role="financiador"),
    "Bearer root": UserInfo(username="root", display_name="Root", role="super_admin"),
    "Bearer aud": UserInfo(username="aud", display_name="Auditor", role="auditor"),
}


def _auth_falso(authorization):
    """Resuelve el usuario a partir del header, sin sesiones reales."""
    usuario = _USUARIOS.get(authorization or "")
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")
    return usuario


@pytest.fixture()
def cliente(monkeypatch):
    """App de prueba con el router del financiador sobre la red Fabric fake."""
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "100")
    repo = FabricPrescriptionRepository(FakeFabricClient())
    canonical = build_canonical_payload(
        {"patient_id": 1, "edad": 70, "estadio": "IV", "m": "M1", "id_regimen": "R07"},
        {"estado": "REVISION"},
        "2026-10-05T10:00:00Z",
    )
    repo.create("01A", canonical)
    servicio = FinanciadorService(repo)

    def _servicio():
        """Servicio del financiador de prueba."""
        return servicio

    monkeypatch.setattr(modulo, "require_auth", _auth_falso)
    monkeypatch.setattr(modulo, "get_financiador_service", _servicio)
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(modulo.router)
    return TestClient(app)


def test_el_financiador_ve_el_resumen(cliente):
    respuesta = cliente.get("/financiador/resumen", headers={"Authorization": "Bearer fin"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["prescripciones_analizadas"] == 1
    assert cuerpo["surge_potencialmente_recuperables"] == 1


def test_el_super_admin_ve_los_expedientes_filtrados(cliente):
    cabecera = {"Authorization": "Bearer root"}
    respuesta = cliente.get("/financiador/expedientes?surge=true", headers=cabecera)
    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 1
    vacia = cliente.get("/financiador/expedientes?alternativa=adoptada", headers=cabecera)
    assert vacia.json()["total"] == 0


def test_el_auditor_no_accede_al_panel(cliente):
    assert cliente.get("/financiador/resumen", headers={"Authorization": "Bearer aud"}).status_code == 403
    assert cliente.get("/financiador/expedientes", headers={"Authorization": "Bearer aud"}).status_code == 403


def test_sin_sesion_responde_401(cliente):
    assert cliente.get("/financiador/resumen").status_code == 401
    assert cliente.get("/financiador/expedientes").status_code == 401


def test_el_financiador_lee_fabric_como_prepaga():
    usuario = UserInfo(username="fin", display_name="Prepaga", role="financiador")
    assert modulo_prescripciones._actor_for(usuario) == "prepaga"
