"""Flujo on-chain de prescripciones y auditoria contra el fake del chaincode."""

import pytest

from backend.blockchain.fabric_client import FabricBusinessError
from backend.error_handlers import ConflictError, NotFoundError
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import build_canonical_payload
from backend.services.audit_service import AuditService
from tests.fakes.fake_fabric_gateway import FakeFabricClient


@pytest.fixture()
def fake():
    return FakeFabricClient()


@pytest.fixture()
def repo(fake):
    return FabricPrescriptionRepository(fake)


@pytest.fixture()
def audit(repo):
    return AuditService(repo)


def _clinical(patient_id=1):
    """Bloque clinico completo (todos los campos requeridos por ClinicalData)."""
    return {
        "patient_id": patient_id,
        "edad": 61,
        "sexo": "F",
        "peso_kg": 70.5,
        "talla_cm": 165.0,
        "superficie_corporal_m2": 1.8,
        "diagnostico_cie10": "C18.9",
        "localizacion_tumor": "colon ascendente",
        "tipo_histologico": "adenocarcinoma",
        "t": "T3",
        "n": "N1",
        "m": "M0",
        "estadio": "III",
        "msi": "MSS",
        "ras": "wild_type",
        "braf_v600e": "no_evaluado",
        "linea_tratamiento": "1L",
        "id_regimen": "R03",
        "esquema": "FOLFOX",
        "dosis_por_farmaco": [{"monodroga": "OXALIPLATINO", "dosis_mg": 153.0}],
        "dosis_mg_m2": 85.0,
        "medico_prescriptor": "Dra. Perez",
        "matricula": "MN 12345",
    }


def _crear(repo, prescription_id="01A", patient_id=1, created_at="2026-03-01T00:00:00Z"):
    canonical = build_canonical_payload(
        _clinical(patient_id),
        {"estado": "APROBADO", "probabilidad_concordante": 0.91},
        created_at,
    )
    return repo.create(prescription_id, canonical)


def test_create_nace_pendiente_de_auditoria(repo):
    result = _crear(repo)
    asset = result["asset"]
    assert asset["estado"] == "PENDIENTE_AUDITORIA"
    assert asset["prescription_code"] == "PRESC-01A"
    assert asset["payload_hash"] == asset["current_hash"]
    assert asset["created_by_msp"] == "PrescriptorMSP"
    assert result["tx_id"]


def test_create_es_idempotente_por_id(repo):
    _crear(repo)
    with pytest.raises(FabricBusinessError) as exc_info:
        _crear(repo)
    assert repo.is_already_exists(exc_info.value)


def test_solo_el_prescriptor_puede_crear(fake):
    canonical = build_canonical_payload({"patient_id": 1}, {"estado": "APROBADO"}, "2026-03-01T00:00:00Z")
    with pytest.raises(FabricBusinessError):
        fake.invoke("CreatePrescription", ["01B", canonical], actor="auditor")


def test_solo_el_auditor_puede_auditar(fake, repo):
    _crear(repo)
    with pytest.raises(FabricBusinessError):
        fake.invoke("AuditPrescription", ["01A", "aprobar", "ok", "aud"], actor="prescriptor")


def test_flujo_revision_y_dictamen_final(repo, audit):
    _crear(repo)

    en_revision = audit.accion("01A", "revision", "faltan estudios", "aud1")
    assert en_revision.estado == "EN_REVISION"
    assert en_revision.audit_events[0].accion == "revision"
    assert en_revision.audit_events[0].prev_hash == en_revision.payload_hash

    aprobada = audit.accion("01A", "aprobar", "estudios completos", "aud1")
    assert aprobada.estado == "APROBADA"
    assert len(aprobada.audit_events) == 2
    # La cadena de hashes avanza con cada accion.
    assert aprobada.current_hash == aprobada.audit_events[1].event_hash
    assert aprobada.audit_events[1].prev_hash == aprobada.audit_events[0].event_hash


def test_dictamen_directo_sin_revision(repo, audit):
    _crear(repo)
    rechazada = audit.accion("01A", "rechazar", "no cumple guias", "aud2")
    assert rechazada.estado == "RECHAZADA"


def test_estado_terminal_no_admite_mas_acciones(repo, audit):
    _crear(repo)
    audit.accion("01A", "aprobar", "ok", "aud1")
    with pytest.raises(ConflictError):
        audit.accion("01A", "rechazar", "cambio de opinion", "aud1")
    with pytest.raises(ConflictError):
        audit.accion("01A", "revision", "reabrir", "aud1")


def test_accion_sobre_inexistente_da_not_found(audit):
    with pytest.raises(NotFoundError):
        audit.accion("NOEXISTE", "aprobar", "ok", "aud1")


def test_cola_de_auditoria_filtra_por_estado(repo, audit):
    _crear(repo, "01A", patient_id=1, created_at="2026-03-01T00:00:00Z")
    _crear(repo, "01B", patient_id=2, created_at="2026-03-02T00:00:00Z")
    _crear(repo, "01C", patient_id=1, created_at="2026-03-03T00:00:00Z")
    audit.accion("01B", "revision", "faltan estudios", "aud1")
    audit.accion("01C", "aprobar", "ok", "aud1")

    pendientes = audit.queue(estado="PENDIENTE_AUDITORIA")
    assert [p.prescription_id for p in pendientes.prescriptions] == ["01A"]

    en_revision = audit.queue(estado="EN_REVISION")
    assert [p.prescription_id for p in en_revision.prescriptions] == ["01B"]


def test_cola_rechaza_estados_terminales(audit):
    with pytest.raises(ConflictError):
        audit.queue(estado="APROBADA")


def test_listado_paginado_por_bookmark(repo):
    for i in range(5):
        _crear(repo, f"01{chr(65 + i)}", created_at=f"2026-03-0{i + 1}T00:00:00Z")

    pagina1 = repo.list(page_size=2)
    assert len(pagina1["items"]) == 2
    assert pagina1["bookmark"]
    # Mas recientes primero (ULID/id descendente).
    assert pagina1["items"][0]["prescription_id"] == "01E"

    pagina2 = repo.list(page_size=2, bookmark=pagina1["bookmark"])
    assert len(pagina2["items"]) == 2
    ids1 = {a["prescription_id"] for a in pagina1["items"]}
    ids2 = {a["prescription_id"] for a in pagina2["items"]}
    assert not ids1 & ids2


def test_busqueda_por_paciente(repo):
    _crear(repo, "01A", patient_id=1)
    _crear(repo, "01B", patient_id=2)
    _crear(repo, "01C", patient_id=1)

    del_paciente = repo.list_by_patient(1)
    assert {a["prescription_id"] for a in del_paciente["items"]} == {"01A", "01C"}


def test_historial_registra_cada_transaccion(repo, audit):
    _crear(repo)
    audit.accion("01A", "revision", "faltan estudios", "aud1")
    audit.accion("01A", "aprobar", "ok", "aud1")

    history = repo.history("01A")
    assert len(history) == 3
    assert all(entry["tx_id"] for entry in history)
