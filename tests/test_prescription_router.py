"""Endpoints de prescripciones: roles, alta firmada, lectura, historial y verificaciones."""

import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.error_handlers import install_error_handlers
from backend.models.auth import UserInfo
from backend.models.prescription import ValidationResult
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.repositories.signing_key_repo import SigningKeyRepository
from backend.security.crypto import CryptoService
from backend.services.dosis_service import DosisService
from backend.services.prescription_service import PrescriptionService
from backend.services.recomendacion_service import RecomendacionService
from backend.services.signing_service import SigningService
from tests.fakes.fake_fabric_gateway import FakeFabricClient
from tests.test_motor_emision import _CATALOGO, _CatalogoFake

# backend.routers reexporta el objeto router con el mismo nombre que el modulo.
modulo = importlib.import_module("backend.routers.prescription_router")

_CRYPTO = CryptoService(os.urandom(32))

_USUARIOS = {
    "Bearer presc": UserInfo(username="presc", display_name="Dra. Perez", role="prescriptor"),
    "Bearer aud": UserInfo(username="aud", display_name="Auditor", role="auditor"),
    "Bearer admin": UserInfo(username="admin", display_name="Admin", role="administrador"),
    "Bearer root": UserInfo(username="root", display_name="Root", role="super_admin"),
}


def _crypto():
    """Proveedor de CryptoService para los tests."""
    return _CRYPTO


def _auth_falso(authorization):
    """Resuelve el usuario a partir del header, sin sesiones reales."""
    from fastapi import HTTPException

    usuario = _USUARIOS.get(authorization or "")
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesion invalida o expirada.")
    return usuario


class _ValidacionStub:
    """Motor de validacion fijo."""

    def validate(self, data):
        """Devuelve siempre un veredicto aprobado."""
        return ValidationResult(estado="APROBADO", probabilidad_concordante=0.9)


class _PacientesStub:
    """Padron con el paciente 1."""

    def exists(self, patient_id):
        """Solo existe el paciente 1."""
        return patient_id == 1


_BODY = {
    "patient_id": 1,
    "edad": 61,
    "sexo": "Femenino",
    "peso_kg": 70.0,
    "talla_cm": 165.0,
    "diagnostico_cie10": "C18.7",
    "localizacion_tumor": "colon izquierdo",
    "tipo_histologico": "Adenocarcinoma",
    "t": "T3",
    "n": "N1",
    "m": "M0",
    "estadio": "III",
    "linea_tratamiento": "Adyuvancia",
    "id_regimen": "R02",
    "dosis_por_farmaco": [{"monodroga": "oxaliplatino", "dosis_mg": 230.0}],
    "medico_prescriptor": "Dra. Perez",
    "matricula": "MN 12345",
}


@pytest.fixture()
def cliente(monkeypatch):
    """App de prueba con el router y servicios sobre la red Fabric fake."""
    dosis = DosisService(_CatalogoFake(_CATALOGO))
    servicio = PrescriptionService(
        FabricPrescriptionRepository(FakeFabricClient()),
        _ValidacionStub(),
        dosis_service=dosis,
        patient_service=_PacientesStub(),
        signing_service=SigningService(SigningKeyRepository(), _crypto),
    )

    def _servicio():
        """Servicio de prescripciones de prueba."""
        return servicio

    def _dosis():
        """Servicio de dosis de prueba."""
        return dosis

    def _recomendacion():
        """Servicio de recomendacion de prueba."""
        return RecomendacionService(dosis)

    monkeypatch.setattr(modulo, "require_auth", _auth_falso)
    monkeypatch.setattr(modulo, "get_prescription_service", _servicio)
    monkeypatch.setattr(modulo, "get_dosis_service", _dosis)
    monkeypatch.setattr(modulo, "get_recomendacion_service", _recomendacion)
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(modulo.router)
    return TestClient(app)


def _alta(cliente):
    """Da de alta una prescripcion como prescriptor."""
    respuesta = cliente.post("/prescriptions", json=_BODY, headers={"Authorization": "Bearer presc"})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_catalogo_de_regimenes(cliente):
    respuesta = cliente.get("/prescriptions/regimenes", headers={"Authorization": "Bearer aud"})
    assert respuesta.status_code == 200
    assert len(respuesta.json()["regimenes"]) == 14


def test_sin_sesion_responde_401(cliente):
    assert cliente.get("/prescriptions/regimenes").status_code == 401


def test_dosis_de_referencia(cliente):
    respuesta = cliente.get(
        "/prescriptions/dosis-referencia?id_regimen=R02&peso_kg=70&talla_cm=165",
        headers={"Authorization": "Bearer presc"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()[0]["monodroga"] == "oxaliplatino"


def test_recomendacion_por_guias(cliente):
    respuesta = cliente.post(
        "/prescriptions/recomendacion",
        json={"estadio": "IV", "msi": "MSI-H", "peso_kg": 70, "talla_cm": 165},
        headers={"Authorization": "Bearer presc"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["id_regimen"] == "R09"


def test_el_auditor_no_puede_prescribir(cliente):
    respuesta = cliente.post("/prescriptions", json=_BODY, headers={"Authorization": "Bearer aud"})
    assert respuesta.status_code == 403


def test_alta_firmada_y_lecturas(cliente):
    creada = _alta(cliente)
    pid = creada["prescription_id"]
    assert creada["clinical"]["firma"]["firmante"] == "presc"
    cabecera = {"Authorization": "Bearer aud"}

    assert cliente.get("/prescriptions/%s" % pid, headers=cabecera).json()["prescription_id"] == pid
    assert cliente.get("/prescriptions", headers=cabecera).json()["prescriptions"]
    assert cliente.get("/prescriptions?estado=PENDIENTE_AUDITORIA", headers=cabecera).status_code == 200
    assert cliente.get("/prescriptions/by-patient/1", headers=cabecera).json()["prescriptions"]
    assert cliente.get("/prescriptions/%s/history" % pid, headers=cabecera).json()["history"]
    assert cliente.get("/prescriptions/%s/verify" % pid, headers=cabecera).json()["valido"]
    firma = cliente.get("/prescriptions/%s/firma/verificacion" % pid, headers=cabecera).json()
    assert firma["estado"] == "valida"


def test_lectura_con_rol_de_prepaga(cliente):
    _alta(cliente)
    respuesta = cliente.get("/prescriptions", headers={"Authorization": "Bearer root"})
    assert respuesta.status_code == 200


def test_estado_invalido_en_el_filtro(cliente):
    respuesta = cliente.get("/prescriptions?estado=OTRO", headers={"Authorization": "Bearer aud"})
    assert respuesta.status_code == 422


def test_paciente_inexistente(cliente):
    cuerpo = dict(_BODY, patient_id=99)
    respuesta = cliente.post("/prescriptions", json=cuerpo, headers={"Authorization": "Bearer presc"})
    assert respuesta.status_code == 422


def test_prescripcion_inexistente(cliente):
    cabecera = {"Authorization": "Bearer aud"}
    assert cliente.get("/prescriptions/NOEXISTE", headers=cabecera).status_code == 404
    assert cliente.get("/prescriptions/NOEXISTE/verify", headers=cabecera).status_code == 404
    assert cliente.get("/prescriptions/NOEXISTE/history", headers=cabecera).status_code == 404
    assert cliente.get("/prescriptions/NOEXISTE/firma/verificacion", headers=cabecera).status_code == 404


def test_el_administrador_de_datos_no_lee_prescripciones(cliente):
    respuesta = cliente.get("/prescriptions", headers={"Authorization": "Bearer admin"})
    assert respuesta.status_code == 403
