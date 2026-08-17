"""Vectores de hash compartidos con el chaincode Go y verificacion de cadena.

Los vectores de este archivo estan espejados en
chaincode/prescription-contract/contract_test.go: el mismo JSON canonico y el
mismo eslabon de auditoria deben producir exactamente los mismos SHA-256 en
Python y en Go. Si alguno de estos tests rompe, la convencion de docs/HASHING.md
divergio entre lenguajes.
"""

import json

from backend.security.canonical import (
    ACCION_A_ESTADO,
    TRANSICIONES_VALIDAS,
    build_canonical_payload,
    canonical_json,
    compute_event_hash,
    sha256_hex,
    verify_chain,
)

VECTOR_CANONICO = '{"clinical":{"a":1},"created_at":"2026-01-01T00:00:00Z","ml":{"b":2}}'
VECTOR_PAYLOAD_HASH = "4812d96106eb7f21fd0da9b6fafcf23b5cb3dba5964e95feb93970898f97ebc4"
VECTOR_EVENT_HASH = "92254dfc8a7257b357b95c7564f9e12d4eabfa7b21453203ed4b2a87e3218b5f"


def test_payload_hash_vector_compartido():
    """El vector canonico produce el mismo hash que en contract_test.go."""
    assert sha256_hex(VECTOR_CANONICO) == VECTOR_PAYLOAD_HASH


def test_build_canonical_payload_reproduce_el_vector():
    """build_canonical_payload arma exactamente el string del vector."""
    payload = build_canonical_payload({"a": 1}, {"b": 2}, "2026-01-01T00:00:00Z")
    assert payload == VECTOR_CANONICO


def test_event_hash_vector_compartido():
    """El eslabon de auditoria produce el mismo hash que en contract_test.go."""
    got = compute_event_hash(
        "0" * 64,
        "aprobar",
        "APROBADA",
        "auditor1",
        "Cumple guias clinicas",
        "2026-01-01T00:00:00Z",
    )
    assert got == VECTOR_EVENT_HASH


def test_canonical_json_es_deterministico():
    """Mismo contenido con distinto orden de claves -> mismo string canonico."""
    a = canonical_json({"z": 1, "a": {"y": 2.5, "b": [1, 2]}})
    b = canonical_json({"a": {"b": [1, 2], "y": 2.5}, "z": 1})
    assert a == b
    # Round-trip: parsear y re-canonicalizar reproduce el mismo string.
    assert canonical_json(json.loads(a)) == a


def test_tabla_de_transiciones_espejada_con_el_chaincode():
    """Espejo exacto de `transicionesValidas` en contract.go."""
    assert TRANSICIONES_VALIDAS == {
        "PENDIENTE_AUDITORIA": ("EN_REVISION", "APROBADA", "RECHAZADA"),
        "EN_REVISION": ("APROBADA", "RECHAZADA"),
        "APROBADA": (),
        "RECHAZADA": (),
    }
    assert ACCION_A_ESTADO == {
        "revision": "EN_REVISION",
        "aprobar": "APROBADA",
        "rechazar": "RECHAZADA",
    }


def _asset_de_ejemplo() -> dict:
    """Crea un asset valido usando el fake (misma semantica que el chaincode)."""
    from tests.fakes.fake_fabric_gateway import FakeFabricClient

    fake = FakeFabricClient()
    canonical = build_canonical_payload(
        {"patient_id": 7, "estadio": "III"}, {"estado": "APROBADO"}, "2026-02-02T10:00:00Z"
    )
    fake.invoke("CreatePrescription", ["01TEST", canonical], actor="prescriptor")
    fake.invoke("AuditPrescription", ["01TEST", "revision", "pedir estudios", "aud1"], actor="auditor")
    fake.invoke("AuditPrescription", ["01TEST", "aprobar", "estudios correctos", "aud1"], actor="auditor")
    return json.loads(fake.query("GetPrescription", ["01TEST"]))


def test_verify_chain_acepta_un_asset_integro():
    asset = _asset_de_ejemplo()
    resultado = verify_chain(asset)
    assert resultado["valido"], resultado["errores"]


def test_verify_chain_detecta_adulteracion_clinica():
    asset = _asset_de_ejemplo()
    asset["clinical"]["estadio"] = "I"  # adulteracion del dato clinico
    resultado = verify_chain(asset)
    assert not resultado["valido"]
    assert any("payload_hash" in e for e in resultado["errores"])


def test_verify_chain_detecta_adulteracion_de_dictamen():
    asset = _asset_de_ejemplo()
    asset["audit_events"][1]["justificacion"] = "texto adulterado"
    resultado = verify_chain(asset)
    assert not resultado["valido"]
    assert any("evento 2" in e for e in resultado["errores"])


def test_verify_chain_detecta_cadena_rota():
    asset = _asset_de_ejemplo()
    asset["audit_events"][1]["prev_hash"] = "f" * 64
    resultado = verify_chain(asset)
    assert not resultado["valido"]
