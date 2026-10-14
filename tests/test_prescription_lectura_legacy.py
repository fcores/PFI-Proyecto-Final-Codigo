"""La lectura de assets on-chain no aplica las validaciones del alta.

El ledger es inmutable: guarda prescripciones escritas con reglas anteriores.
Si el modelo de lectura validara como el de entrada, un solo asset viejo
haria fallar con 500 el historial, la cola de auditoria y la trazabilidad.
"""

import json

import pytest

from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import build_canonical_payload
from backend.services.audit_service import AuditService
from backend.services.prescription_service import PrescriptionService, _asset_to_prescription
from tests.fakes.fake_fabric_gateway import FakeFabricClient

_CLINICAL = {
    "patient_id": 1,
    "edad": 61,
    "sexo": "F",
    "peso_kg": 70,
    "talla_cm": 165,
    "superficie_corporal_m2": 1.8,
    "diagnostico_cie10": "C18.9",
    "localizacion_tumor": "colon",
    "tipo_histologico": "adenocarcinoma",
    "t": "T3",
    "n": "N1",
    "m": "M0",
    "estadio": "III",
    "linea_tratamiento": "1L",
    "id_regimen": "R03",
    "medico_prescriptor": "Dra. Perez",
    "matricula": "MN 1",
}

LEGACY = [
    ("diagnostico_cie10", "Adenocarcinoma de colon sigmoide"),
    ("id_regimen", "FOLFOX"),
    ("patient_id", 0),
    ("t", ""),
    ("linea_tratamiento", "adyuvancia con capecitabina post cirugia de colon izquierdo"),
    ("peso_kg", 900),
    ("dosis_por_farmaco", [{"monodroga": "x" * 300, "dosis_mg": -1}]),
]


def _asset(clinical):
    return {
        "prescription_id": "01A",
        "prescription_code": "PRESC-01A",
        "estado": "PENDIENTE_AUDITORIA",
        "clinical": clinical,
        "ml": {"estado": "APROBADO"},
        "created_at": "2026-01-01T00:00:00Z",
        "payload_hash": "h",
        "current_hash": "h",
    }


@pytest.mark.parametrize("campo,valor", LEGACY)
def test_asset_que_no_cumple_las_reglas_actuales_se_lee_igual(campo, valor):
    presc = _asset_to_prescription(_asset({**_CLINICAL, campo: valor}))
    assert getattr(presc.clinical, campo) == valor


def test_asset_con_campos_faltantes_o_desconocidos_se_lee_igual():
    clinical = {k: v for k, v in _CLINICAL.items() if k not in ("msi", "matricula", "estadio")}
    clinical["campo_de_una_version_futura"] = "valor"
    presc = _asset_to_prescription(_asset(clinical))
    assert presc.clinical.estadio is None
    # Los campos no declarados se devuelven igual (el frontend muestra lo registrado).
    assert presc.model_dump()["clinical"]["campo_de_una_version_futura"] == "valor"


def test_un_asset_viejo_no_rompe_el_listado_ni_la_cola():
    fake = FakeFabricClient()
    repo = FabricPrescriptionRepository(fake)
    viejo = {**_CLINICAL, "diagnostico_cie10": "Adenocarcinoma de colon sigmoide", "id_regimen": "FOLFOX"}
    repo.create("01VIEJO", build_canonical_payload(viejo, {"estado": "REVISION"}, "2026-01-01T00:00:00Z"))
    repo.create("01NUEVO", build_canonical_payload(_CLINICAL, {"estado": "APROBADO"}, "2026-02-01T00:00:00Z"))

    listado = PrescriptionService(repo, validation_service=None).list()
    assert {p.prescription_id for p in listado.prescriptions} == {"01VIEJO", "01NUEVO"}

    cola = AuditService(repo).queue("PENDIENTE_AUDITORIA")
    assert len(cola.prescriptions) == 2

    detalle = AuditService(repo).detail("01VIEJO")
    assert detalle.prescription.clinical.diagnostico_cie10 == "Adenocarcinoma de colon sigmoide"
    assert json.loads(fake.query("GetPrescription", ["01VIEJO"]))["clinical"]["id_regimen"] == "FOLFOX"
