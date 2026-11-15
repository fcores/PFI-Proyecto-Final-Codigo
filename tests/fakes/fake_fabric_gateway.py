"""Fake del puente Fabric para tests sin red.

Replica la semantica del chaincode prescription-contract (idempotencia,
maquina de estados, control de acceso por actor/MSP, hashing encadenado y
paginacion por bookmark) sobre un dict en memoria. Implementa la misma
interfaz que backend.blockchain.fabric_client.FabricClient, por lo que se
inyecta directo en FabricPrescriptionRepository.

La tabla de transiciones y las formulas de hash se importan de
backend.security.canonical, que a su vez esta espejada con contract.go
(verificado por los vectores compartidos de tests/test_canonical_hash.py).
"""

import json
from datetime import UTC, datetime

from backend.blockchain.fabric_client import FabricBusinessError
from backend.security.canonical import (
    ACCION_A_ESTADO,
    TRANSICIONES_VALIDAS,
    compute_event_hash,
    sha256_hex,
)


class FakeFabricClient:
    """Doble de FabricClient con la semantica del chaincode en memoria."""

    available = True

    def __init__(self) -> None:
        self.state: dict[str, dict] = {}
        self.history_log: dict[str, list] = {}
        self._tx_counter = 0

    def health(self) -> dict:
        return {"status": "ok", "service": "fake-fabric-gateway", "orgs": {}}

    # ── interfaz FabricClient ────────────────────────────────────────────────

    def invoke(self, function: str, args: list[str], actor: str) -> dict:
        if function == "CreatePrescription":
            if actor != "prescriptor":
                raise FabricBusinessError(
                    "la funcion CreatePrescription requiere actor=prescriptor",
                    error_type="bad_request",
                )
            return self._create(args[0], args[1])
        if function == "AuditPrescription":
            if actor != "auditor":
                raise FabricBusinessError(
                    "la funcion AuditPrescription requiere actor=auditor",
                    error_type="bad_request",
                )
            return self._audit(args[0], args[1], args[2], args[3])
        if function == "InitLedger":
            return {"tx_id": self._next_tx(), "payload": ""}
        raise FabricBusinessError(f"funcion de escritura desconocida: {function}", error_type="bad_request")

    def query(self, function: str, args: list[str], actor: str = "prepaga") -> str:
        if function == "GetPrescription":
            asset = self.state.get(args[0])
            if asset is None:
                raise FabricBusinessError(f"prescripcion {args[0]} no encontrada", error_type="evaluate")
            return json.dumps(asset)
        if function == "ListPrescriptions":
            items = sorted(self.state.values(), key=lambda a: a["prescription_id"], reverse=True)
            return self._paginate(items, int(args[0]), args[1])
        if function == "QueryPrescriptionsByEstado":
            estado = args[0]
            items = sorted(
                (a for a in self.state.values() if a["estado"] == estado),
                key=lambda a: a["created_at"],
            )
            return self._paginate(items, int(args[1]), args[2])
        if function == "QueryPrescriptionsByPatient":
            pid = int(args[0])
            items = sorted(
                (a for a in self.state.values() if a["clinical"].get("patient_id") == pid),
                key=lambda a: a["created_at"],
            )
            return self._paginate(items, int(args[1]), args[2])
        if function == "GetPrescriptionHistory":
            return json.dumps(self.history_log.get(args[0], []))
        raise FabricBusinessError(f"funcion de lectura desconocida: {function}", error_type="bad_request")

    # ── semantica del chaincode ──────────────────────────────────────────────

    def _next_tx(self) -> str:
        self._tx_counter += 1
        return f"faketx_{self._tx_counter:06d}"

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _snapshot(self, prescription_id: str, tx_id: str) -> None:
        asset = self.state[prescription_id]
        self.history_log.setdefault(prescription_id, []).append(
            {
                "tx_id": tx_id,
                "value": json.loads(json.dumps(asset)),
                "timestamp": self._now(),
                "is_delete": False,
            }
        )

    def _create(self, prescription_id: str, canonical_json: str) -> dict:
        if not prescription_id:
            raise FabricBusinessError("prescription_id vacio", error_type="endorse")
        if prescription_id in self.state:
            raise FabricBusinessError(
                f"la prescripcion {prescription_id} ya existe (idempotencia)",
                error_type="endorse",
            )
        payload = json.loads(canonical_json)
        if not payload.get("clinical") or not payload.get("ml") or not payload.get("created_at"):
            raise FabricBusinessError(
                "payload canonico incompleto: se requieren clinical, created_at y ml",
                error_type="endorse",
            )

        payload_hash = sha256_hex(canonical_json)
        asset = {
            "docType": "prescription",
            "prescription_id": prescription_id,
            "prescription_code": "PRESC-" + prescription_id,
            "estado": "PENDIENTE_AUDITORIA",
            "clinical": payload["clinical"],
            "ml": payload["ml"],
            "created_at": payload["created_at"],
            "created_by_msp": "PrescriptorMSP",
            "payload_hash": payload_hash,
            "current_hash": payload_hash,
            "audit_events": [],
        }
        tx = self._next_tx()
        self.state[prescription_id] = asset
        self._snapshot(prescription_id, tx)
        return {"tx_id": tx, "payload": json.dumps(asset)}

    def _audit(self, prescription_id: str, accion: str, justificacion: str, auditor: str) -> dict:
        asset = self.state.get(prescription_id)
        if asset is None:
            raise FabricBusinessError(f"prescripcion {prescription_id} no encontrada", error_type="endorse")
        if not auditor:
            raise FabricBusinessError("auditor vacio", error_type="endorse")
        estado_nuevo = ACCION_A_ESTADO.get(accion)
        if estado_nuevo is None:
            raise FabricBusinessError(f"accion desconocida: {accion}", error_type="endorse")
        if estado_nuevo not in TRANSICIONES_VALIDAS.get(asset["estado"], ()):
            raise FabricBusinessError(
                f"transicion invalida: {asset['estado']} -> {estado_nuevo}",
                error_type="endorse",
            )

        timestamp = self._now()
        prev = asset["current_hash"]
        event_hash = compute_event_hash(prev, accion, estado_nuevo, auditor, justificacion, timestamp)
        tx = self._next_tx()
        asset["audit_events"].append(
            {
                "seq": len(asset["audit_events"]) + 1,
                "accion": accion,
                "estado_resultante": estado_nuevo,
                "auditor": auditor,
                "justificacion": justificacion,
                "timestamp": timestamp,
                "tx_id": tx,
                "prev_hash": prev,
                "event_hash": event_hash,
            }
        )
        asset["estado"] = estado_nuevo
        asset["current_hash"] = event_hash
        self._snapshot(prescription_id, tx)
        return {"tx_id": tx, "payload": json.dumps(asset)}

    @staticmethod
    def _paginate(items: list, page_size: int, bookmark: str) -> str:
        offset = int(bookmark) if bookmark else 0
        page = items[offset : offset + page_size]
        siguiente = offset + len(page)
        next_bookmark = str(siguiente) if siguiente < len(items) else ""
        return json.dumps({"items": page, "fetched_count": len(page), "bookmark": next_bookmark})
