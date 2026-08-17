# Convención de hashing de prescripciones

Este documento define la convención de integridad de las prescripciones
on-chain. Está implementada de forma espejada en:

- **Backend (Python)**: `backend/security/canonical.py`
- **Chaincode (Go)**: `chaincode/prescription-contract/contract.go`
- **Vectores de prueba compartidos**: `tests/test_canonical_hash.py` y
  `chaincode/prescription-contract/contract_test.go` — el mismo input debe
  producir exactamente el mismo SHA-256 en ambos lenguajes.

## 1. JSON canónico

Un documento JSON es *canónico* cuando:

1. Las claves de todos los objetos están ordenadas **alfabéticamente**.
2. No hay espacios en blanco (`separators=(",", ":")` en Python).
3. La codificación es UTF-8 sin escape ASCII (`ensure_ascii=False`).

En Python: `json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.

## 2. Payload canónico de una prescripción

El backend arma el payload que viaja a `CreatePrescription` con exactamente
tres claves (ya en orden alfabético):

```json
{"clinical":{...},"created_at":"2026-08-17T12:00:00Z","ml":{...}}
```

- `clinical`: todos los datos clínicos (paciente seudonimizado vía
  `patient_id`, antropometría, TNM, biomarcadores, régimen, dosis, médico).
- `created_at`: RFC3339 UTC con precisión de segundos, generado por el backend.
- `ml`: el veredicto completo del motor reglas + ML (estado, motivos,
  probabilidad, umbrales, features relevantes, costos).

## 3. payload_hash

```
payload_hash = SHA256(payload_canónico)   // sobre los bytes UTF-8 exactos
```

**El chaincode hashea el string exacto recibido** como argumento — nunca
re-serializa — y almacena `clinical`/`ml` como JSON crudo
(`json.RawMessage`), byte a byte igual al payload. Por eso cualquier
verificador externo puede:

1. Tomar `clinical`, `ml` y `created_at` del asset.
2. Re-canonicalizar (`{"clinical":...,"created_at":"...","ml":...}`).
3. Recomputar SHA-256 y comparar contra `payload_hash`.

**Nota sobre números**: Python serializa floats con la representación más
corta que round-trippea (repr). Como el chaincode no re-serializa y la
verificación parte de los valores parseados (mismo double IEEE-754), la
representación es estable de punta a punta, incluso pasando por CouchDB.

## 4. Cadena de eventos de auditoría (event_hash)

Cada acción del auditor (`revision` | `aprobar` | `rechazar`) encadena un
nuevo eslabón:

```
h0 = payload_hash
event_hash_i = SHA256(
    prev_hash + "|" + accion + "|" + estado_resultante + "|" + auditor
    + "|" + SHA256(justificacion) + "|" + timestamp
)
current_hash = event_hash del último evento
```

- `prev_hash` del evento 1 es `payload_hash`; de ahí en más, el `event_hash`
  del evento anterior.
- `timestamp` es RFC3339 UTC con precisión de segundos y proviene de
  `GetTxTimestamp()` (el timestamp del proposal del cliente: idéntico para
  los tres endorsers — **nunca** `time.Now()`, que rompería el endorsement
  AND de las 3 organizaciones).
- La `justificacion` se hashea aparte para que el material del eslabón tenga
  largo acotado y no dependa de caracteres especiales.

## 5. Verificación

- **Backend**: `GET /api/prescriptions/{id}/verify` ejecuta
  `verify_chain(asset)` y reporta `{valido, errores}`. Chequea el
  `payload_hash`, el encadenamiento de cada evento y que `current_hash` sea
  el último eslabón.
- **Externa**: cualquiera de las tres organizaciones (o un tercero con el
  asset en mano) puede replicar los pasos 2–4 sin acceso al backend.

## 6. Vectores de prueba compartidos

| Vector | Valor |
|---|---|
| Payload canónico | `{"clinical":{"a":1},"created_at":"2026-01-01T00:00:00Z","ml":{"b":2}}` |
| `payload_hash` esperado | `4812d96106eb7f21fd0da9b6fafcf23b5cb3dba5964e95feb93970898f97ebc4` |
| Eslabón (`prev=64×"0"`, `aprobar`, `APROBADA`, `auditor1`, `"Cumple guias clinicas"`, `2026-01-01T00:00:00Z`) | `92254dfc8a7257b357b95c7564f9e12d4eabfa7b21453203ed4b2a87e3218b5f` |

Si alguno de los dos lados cambia la convención, estos vectores fallan en CI
(`pytest` y `go test`) y delatan la divergencia.
