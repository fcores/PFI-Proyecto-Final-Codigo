"""
Repositorio de prescripciones sobre Hyperledger Fabric.

Unica pieza del backend que conoce los nombres de las funciones del chaincode
`prescriptions` y el mapeo JSON <-> dominio. Recibe el FabricClient por
constructor para poder inyectar un fake en tests.

La prescripcion NO existe en la RDS: toda lectura y escritura pasa por aca.
"""

# Annotations diferidas: la clase define un metodo `list` que ensombrece al
# builtin dentro del cuerpo de la clase.
from __future__ import annotations

import json
import logging
from typing import Any

from backend.blockchain.fabric_client import FabricBusinessError, FabricClient

logger = logging.getLogger(__name__)

_NOT_FOUND_MARKER = "no encontrada"
_ALREADY_EXISTS_MARKER = "ya existe"


class FabricPrescriptionRepository:
    """Acceso a las prescripciones almacenadas en el world state de Fabric."""

    def __init__(self, client: FabricClient) -> None:
        self._client = client

    # ── escrituras ───────────────────────────────────────────────────────────

    def create(self, prescription_id: str, canonical_payload: str) -> dict[str, Any]:
        """Registra la prescripcion on-chain (firma PrescriptorMSP).

        Returns:
            {"tx_id": str, "asset": dict} con el asset tal como quedo on-chain.

        Raises:
            FabricBusinessError: si la red rechaza (incluye "ya existe").
            FabricUnavailableError: si la red no responde.
        """
        result = self._client.invoke(
            "CreatePrescription",
            [prescription_id, canonical_payload],
            actor="prescriptor",
        )
        return {"tx_id": result.get("tx_id"), "asset": _parse_json(result.get("payload"))}

    def audit_action(
        self,
        prescription_id: str,
        accion: str,
        justificacion: str,
        auditor: str,
    ) -> dict[str, Any]:
        """Registra una accion de auditoria on-chain (firma MedChainMSP)."""
        result = self._client.invoke(
            "AuditPrescription",
            [prescription_id, accion, justificacion, auditor],
            actor="auditor",
        )
        return {"tx_id": result.get("tx_id"), "asset": _parse_json(result.get("payload"))}

    # ── lecturas ─────────────────────────────────────────────────────────────

    def get(self, prescription_id: str, actor: str = "prepaga") -> dict[str, Any] | None:
        """Devuelve el asset o None si no existe."""
        try:
            payload = self._client.query("GetPrescription", [prescription_id], actor=actor)
        except FabricBusinessError as exc:
            if _NOT_FOUND_MARKER in str(exc):
                return None
            raise
        return _parse_json(payload)

    def list(self, page_size: int = 50, bookmark: str = "", actor: str = "prepaga") -> dict[str, Any]:
        """Listado general, mas recientes primero. Devuelve {items, fetched_count, bookmark}."""
        payload = self._client.query("ListPrescriptions", [str(page_size), bookmark], actor=actor)
        return _parse_paged(payload)

    def list_by_estado(
        self,
        estado: str,
        page_size: int = 50,
        bookmark: str = "",
        actor: str = "prepaga",
    ) -> dict[str, Any]:
        """Prescripciones por estado, mas antiguas primero (orden del chaincode)."""
        payload = self._client.query("QueryPrescriptionsByEstado", [estado, str(page_size), bookmark], actor=actor)
        return _parse_paged(payload)

    def list_by_patient(
        self,
        patient_id: int,
        page_size: int = 50,
        bookmark: str = "",
        actor: str = "prepaga",
    ) -> dict[str, Any]:
        """Prescripciones de un paciente (seudonimo patient_id), cronologicas."""
        payload = self._client.query(
            "QueryPrescriptionsByPatient", [str(patient_id), str(page_size), bookmark], actor=actor
        )
        return _parse_paged(payload)

    def history(self, prescription_id: str, actor: str = "prepaga") -> list[dict[str, Any]]:
        """Historial de transacciones de la clave (tx_id reales de Fabric)."""
        payload = self._client.query("GetPrescriptionHistory", [prescription_id], actor=actor)
        parsed = _parse_json(payload)
        return parsed if isinstance(parsed, list) else []

    @staticmethod
    def is_already_exists(exc: FabricBusinessError) -> bool:
        """Indica si el error corresponde a la clave ya existente (idempotencia)."""
        return _ALREADY_EXISTS_MARKER in str(exc)


def _parse_json(payload: str | None) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        logger.error("Payload del chaincode no es JSON valido: %.200s", payload)
        raise


def _parse_paged(payload: str | None) -> dict[str, Any]:
    parsed = _parse_json(payload) or {}
    return {
        "items": parsed.get("items") or [],
        "fetched_count": parsed.get("fetched_count", 0),
        "bookmark": parsed.get("bookmark") or "",
    }
