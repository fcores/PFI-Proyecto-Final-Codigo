"""Panel del financiador: agregados de las palancas de costo evitado (RF-40)."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import build_canonical_payload
from backend.services.audit_service import AuditService
from backend.services.financiador_service import FinanciadorService, plazo_vigente
from tests.fakes.fake_fabric_gateway import FakeFabricClient


def _clinical(estadio="III", m="M0", edad=61, id_regimen="R02"):
    """Bloque clinico minimo para el panel."""
    return {
        "patient_id": 1,
        "edad": edad,
        "estadio": estadio,
        "m": m,
        "id_regimen": id_regimen,
        "esquema": "CAPOX",
    }


def _hace(dias):
    """Timestamp RFC3339 de hace la cantidad de dias indicada."""
    return (datetime.now(UTC) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture()
def repo():
    """Repositorio sobre el fake del chaincode."""
    return FabricPrescriptionRepository(FakeFabricClient())


def _crear(repo, pid, clinical, ml, created_at=None):
    """Asienta un asset con el bloque ml dado."""
    canonical = build_canonical_payload(clinical, ml, created_at or _hace(0))
    repo.create(pid, canonical)


@pytest.fixture()
def cargado(repo):
    """Ledger con cuatro casos representativos."""
    _crear(
        repo,
        "01ALERTA",
        _clinical(id_regimen="R01"),
        {
            "estado": "REVISION",
            "requiere_justificacion_costo": True,
            "ahorro_potencial": 4800.0,
            "costo_tratamiento": 12000.0,
        },
    )
    _crear(
        repo,
        "01ADOPTADA",
        _clinical(),
        {"estado": "APROBADO", "regimen_original": "R01", "ahorro_efectivo": 4800.0},
    )
    _crear(
        repo,
        "01ERROR",
        _clinical(estadio="IV", m="M1"),
        {"estado": "RECHAZADO", "origen": "reglas"},
        created_at=_hace(10),
    )
    _crear(
        repo,
        "01SURGE",
        _clinical(estadio="IV", m="M1"),
        {
            "estado": "APROBADO",
            "surge": {"potencialmente_recuperable": True, "norma": "Res. SSSalud 731/2023, Anexo II"},
        },
        created_at=_hace(4),
    )
    AuditService(repo).accion("01ERROR", "rechazar", "anti-EGFR con RAS mutado", "aud1")
    return repo


def test_resumen_agrega_las_palancas(cargado, monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "100")
    resumen = FinanciadorService(cargado).resumen()
    assert resumen.prescripciones_analizadas == 4
    assert resumen.alcanzo_tope is False
    assert resumen.alertas_alternativa == 1
    assert resumen.ahorro_potencial == 4800.0
    assert resumen.alternativas_adoptadas == 1
    assert resumen.ahorro_efectivo == 4800.0
    assert resumen.errores_detectados == 1
    assert resumen.errores_confirmados == 1
    # 01ERROR no tiene la marca asentada: se calcula al leer (adulto, estadio IV).
    assert resumen.surge_potencialmente_recuperables == 2
    assert resumen.plazos.en_plazo == 2
    assert resumen.plazos.por_vencer == 1
    # El dictamen de 01ERROR se registra hoy, dentro de los 30 dias habiles.
    assert resumen.plazos.cumplido == 1


def test_expedientes_filtrables(cargado, monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "100")
    servicio = FinanciadorService(cargado)
    assert servicio.expedientes().total == 4
    assert {e.prescription_id for e in servicio.expedientes(surge=True).expedientes} == {"01ERROR", "01SURGE"}
    assert [e.prescription_id for e in servicio.expedientes(alternativa="alerta").expedientes] == ["01ALERTA"]
    adoptadas = servicio.expedientes(alternativa="adoptada").expedientes
    assert [e.regimen_original for e in adoptadas] == ["R01"]
    assert [e.prescription_id for e in servicio.expedientes(plazo="por_vencer").expedientes] == ["01SURGE"]


def test_el_expediente_no_expone_datos_clinicos_de_detalle(cargado, monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "100")
    expediente = FinanciadorService(cargado).expedientes().expedientes[0]
    campos = set(expediente.model_dump())
    assert "patient_id" not in campos
    assert "edad" not in campos
    assert "diagnostico_cie10" not in campos


def test_respeta_el_tope_de_lectura(cargado, monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "2")
    resumen = FinanciadorService(cargado).resumen()
    assert resumen.prescripciones_analizadas == 2
    assert resumen.alcanzo_tope is True


def test_tope_invalido_usa_el_valor_de_resguardo(cargado, monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "no-numerico")
    assert FinanciadorService(cargado).resumen().prescripciones_analizadas == 4
    monkeypatch.delenv("FINANCIADOR_MAX_PRESCRIPCIONES")
    assert FinanciadorService(cargado).resumen().prescripciones_analizadas == 4


def test_ledger_vacio(repo, monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "100")
    resumen = FinanciadorService(repo).resumen()
    assert resumen.prescripciones_analizadas == 0
    assert resumen.ahorro_potencial == 0.0


def test_plazo_vigente():
    assert plazo_vigente(None) == (None, None)
    assert plazo_vigente({}) == (None, None)
    respuesta = {"estado": "en_plazo", "cumplido_en": None}
    resolucion = {"estado": "en_plazo"}
    assert plazo_vigente({"respuesta": respuesta, "resolucion": resolucion})[0] == "respuesta"
    cumplida = {"estado": "cumplido", "cumplido_en": "2026-10-06T10:00:00Z"}
    assert plazo_vigente({"respuesta": cumplida, "resolucion": resolucion})[0] == "resolucion"
