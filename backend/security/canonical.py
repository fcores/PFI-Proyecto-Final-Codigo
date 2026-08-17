"""
JSON canonico y verificacion de la cadena de hashes de una prescripcion.

Convencion (docs/HASHING.md), espejada con chaincode/prescription-contract:

- canonical_json: claves ordenadas alfabeticamente, separadores sin espacios,
  UTF-8 sin escape ASCII.
- Payload canonico de una prescripcion (claves en orden alfabetico):
      {"clinical":{...},"created_at":"<RFC3339>","ml":{...}}
- payload_hash  = SHA256(payload canonico, byte a byte).
  El chaincode hashea el string EXACTO recibido y almacena clinical/ml como
  JSON crudo, por lo que la verificacion externa consiste en re-canonicalizar
  los campos del asset y recomputar el hash.
- event_hash_i  = SHA256(prev_hash|accion|estado_resultante|auditor|
                         SHA256(justificacion)|timestamp)
  donde prev_hash arranca en payload_hash y cada accion de auditoria encadena
  el siguiente eslabon. current_hash es el ultimo eslabon.

Nota sobre floats: json.dumps de Python usa la representacion mas corta que
round-trippea (repr). Como el chaincode nunca re-serializa el payload y la
verificacion parte de los valores parseados (mismo double IEEE-754), la
representacion es estable de punta a punta.
"""

import hashlib
import json
from typing import Any

TRANSICIONES_VALIDAS = {
    "PENDIENTE_AUDITORIA": ("EN_REVISION", "APROBADA", "RECHAZADA"),
    "EN_REVISION": ("APROBADA", "RECHAZADA"),
    "APROBADA": (),
    "RECHAZADA": (),
}

ACCION_A_ESTADO = {
    "revision": "EN_REVISION",
    "aprobar": "APROBADA",
    "rechazar": "RECHAZADA",
}


def canonical_json(data: Any) -> str:
    """Serializa a JSON canonico: claves ordenadas, sin espacios, UTF-8."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    """SHA-256 en hexadecimal de un string UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_canonical_payload(clinical: dict, ml: dict, created_at: str) -> str:
    """Arma el payload canonico que se envia a CreatePrescription."""
    return canonical_json({"clinical": clinical, "created_at": created_at, "ml": ml})


def compute_event_hash(
    prev_hash: str,
    accion: str,
    estado_resultante: str,
    auditor: str,
    justificacion: str,
    timestamp: str,
) -> str:
    """Replica el eslabon de auditoria que calcula el chaincode."""
    material = "|".join([prev_hash, accion, estado_resultante, auditor, sha256_hex(justificacion), timestamp])
    return sha256_hex(material)


def verify_chain(asset: dict) -> dict:
    """Verifica la integridad de un asset tal como lo devuelve el chaincode.

    Chequea:
      1. payload_hash == SHA256(payload canonico reconstruido de clinical/ml/created_at)
      2. cada audit_event encadena prev_hash y reproduce su event_hash
      3. current_hash == ultimo eslabon

    Returns:
        {"valido": bool, "errores": [str, ...]}
    """
    errores: list[str] = []

    reconstruido = build_canonical_payload(
        asset.get("clinical", {}),
        asset.get("ml", {}),
        asset.get("created_at", ""),
    )
    payload_hash = sha256_hex(reconstruido)
    if payload_hash != asset.get("payload_hash"):
        errores.append("payload_hash no coincide: el contenido clinico/ML no reproduce el hash on-chain")

    prev = asset.get("payload_hash", "")
    for event in asset.get("audit_events", []):
        seq = event.get("seq")
        if event.get("prev_hash") != prev:
            errores.append(f"evento {seq}: prev_hash no encadena con el eslabon anterior")
        esperado = compute_event_hash(
            event.get("prev_hash", ""),
            event.get("accion", ""),
            event.get("estado_resultante", ""),
            event.get("auditor", ""),
            event.get("justificacion", ""),
            event.get("timestamp", ""),
        )
        if esperado != event.get("event_hash"):
            errores.append(f"evento {seq}: event_hash no reproduce el hash on-chain")
        prev = event.get("event_hash", "")

    if asset.get("current_hash") != prev:
        errores.append("current_hash no coincide con el ultimo eslabon de la cadena")

    return {"valido": not errores, "errores": errores}
