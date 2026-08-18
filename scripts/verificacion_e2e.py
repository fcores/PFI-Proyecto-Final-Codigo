"""Verificacion end-to-end de MedChain contra un entorno desplegado.

Recorre el circuito completo —alta on-chain, ciclo de auditoria, trazabilidad—
y despues intenta *romperlo*, que es la parte que realmente demuestra algo:
adultera el asset y comprueba que la cadena de hashes lo detecta.

Uso:
    python scripts/verificacion_e2e.py                    # contra produccion
    python scripts/verificacion_e2e.py http://127.0.0.1:9999   # contra local

Requiere solo la libreria estandar. Se ejecuta desde la raiz del repo porque
reutiliza backend/security/canonical.py: la verificacion externa usa exactamente
el mismo codigo que documenta HASHING.md, no una reimplementacion.

OJO: cada corrida deja una prescripcion real y APROBADA en el ledger, con el
medico "Dr. Verificacion E2E". No se puede borrar (el chaincode no expone
delete y los estados finales son terminales), asi que conviene no abusar contra
produccion. Es demo data, pero se acumula.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from backend.security.canonical import build_canonical_payload, sha256_hex  # noqa: E402

API = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com"

CREDENCIALES = {
    "prescriptor": ("prescriptor", "presc123"),
    "auditor": ("auditor", "audit123"),
    "superadmin": ("superadmin", "super123"),
}

_ok = 0
_fallos = 0


def check(nombre: str, condicion: bool, detalle: str = "") -> bool:
    global _ok, _fallos
    if condicion:
        _ok += 1
        print(f"   OK      {nombre}" + (f"  ({detalle})" if detalle else ""))
    else:
        _fallos += 1
        print(f"   FALLA   {nombre}" + (f"  ({detalle})" if detalle else ""))
    return condicion


def titulo(texto: str) -> None:
    print(f"\n{'=' * 72}\n  {texto}\n{'=' * 72}")


def pedir(path: str, token: str = "", metodo: str = "GET", body=None, tolerar_error=False):
    req = urllib.request.Request(API + path, method=metodo)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    datos = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        datos = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, datos, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if not tolerar_error:
            raise
        cuerpo = e.read().decode()
        try:
            return e.code, json.loads(cuerpo)
        except ValueError:
            return e.code, {"raw": cuerpo}


def login(rol: str) -> str:
    usuario, clave = CREDENCIALES[rol]
    _, r = pedir("/api/auth/login", metodo="POST", body={"username": usuario, "password": clave})
    return r["token"]


def main() -> int:
    print(f"\nVerificacion end-to-end contra {API}")

    # ── 1. La plataforma responde ────────────────────────────────────────────
    titulo("1. Plataforma")
    _, raiz = pedir("/")
    check("API Gateway enruta al backend", raiz.get("status") == "ok")
    check("Backend es el refactorizado", "fabric_gateway" in raiz, "campo fabric_gateway presente")
    check("Backend ve la red Fabric", raiz.get("fabric_gateway") == "ok", str(raiz.get("fabric_gateway")))
    check("RDS conectada", raiz.get("database") == "connected")

    tokens = {rol: login(rol) for rol in CREDENCIALES}
    check("Login de los 3 roles", all(tokens.values()))

    _, salud = pedir("/api/health", tokens["superadmin"])
    orgs = salud.get("fabric_gateway", {}).get("orgs", {})
    check("Las 3 organizaciones en linea", len(orgs) == 3, ", ".join(sorted(orgs)))
    for actor, info in sorted(orgs.items()):
        check(f"  peer {actor} ({info.get('msp_id')})", info.get("status") == "ok")

    # ── 2. Alta on-chain ─────────────────────────────────────────────────────
    titulo("2. Alta de la prescripcion")
    _, pacientes = pedir("/api/patients", tokens["prescriptor"])
    lista = pacientes.get("patients", pacientes)
    if not lista:
        print("   No hay pacientes cargados: corre scripts/poblar_db.py primero.")
        return 1
    paciente = lista[0]

    nueva = {
        "patient_id": paciente["id"],
        "edad": 71, "sexo": "Masculino", "peso_kg": 78.5, "talla_cm": 174,
        "diagnostico_cie10": "C18.2", "localizacion_tumor": "colon_derecho",
        "tipo_histologico": "adenocarcinoma",
        "t": "T3", "n": "N1", "m": "M0", "estadio": "III",
        "msi": "MSS", "ras": "wild_type", "braf_v600e": "wild_type",
        "linea_tratamiento": "adyuvancia", "id_regimen": "R01",
        "medico_prescriptor": "Dr. Verificacion E2E", "matricula": "MN-00000",
    }
    _, presc = pedir("/api/prescriptions", tokens["prescriptor"], "POST", nueva)
    pid = presc.get("prescription_id", "")

    check("Prescripcion creada", bool(pid), pid)
    check("Nace PENDIENTE_AUDITORIA", presc.get("estado") == "PENDIENTE_AUDITORIA", str(presc.get("estado")))
    check("TxID real de Fabric", len(presc.get("tx_id") or "") == 64, (presc.get("tx_id") or "")[:24] + "...")
    check("Trae payload_hash", len(presc.get("payload_hash") or "") == 64)

    # ── 3. Ciclo de auditoria ────────────────────────────────────────────────
    titulo("3. Ciclo de auditoria")
    _, cola = pedir("/api/audit/queue", tokens["auditor"])
    en_cola = [p["prescription_id"] for p in cola.get("prescriptions", [])]
    check("Aparece en la cola del auditor", pid in en_cola, f"{len(en_cola)} en cola")
    check("Cola paginada por bookmark", bool(cola.get("bookmark")))

    _, ev1 = pedir(f"/api/audit/{pid}/accion", tokens["auditor"], "POST",
                   {"accion": "revision", "justificacion": "Solicito RAS actualizado antes de dictaminar."})
    check("Accion 'revision' aceptada", ev1.get("estado") == "EN_REVISION", str(ev1.get("estado")))

    _, ev2 = pedir(f"/api/audit/{pid}/accion", tokens["auditor"], "POST",
                   {"accion": "aprobar", "justificacion": "Esquema y dosis acordes a guias para estadio III."})
    check("Accion 'aprobar' aceptada", ev2.get("estado") == "APROBADA", str(ev2.get("estado")))

    _, hist = pedir(f"/api/prescriptions/{pid}/history", tokens["auditor"])
    txs = hist.get("history", hist.get("items", []))
    check("3 transacciones en el ledger", len(txs) == 3, f"{len(txs)} tx")
    check("Todos los TxID son reales", all(len(t.get("tx_id", "")) == 64 for t in txs))

    # ── 4. Estado terminal ───────────────────────────────────────────────────
    titulo("4. Los estados finales son finales")
    codigo, err = pedir(f"/api/audit/{pid}/accion", tokens["auditor"], "POST",
                        {"accion": "rechazar", "justificacion": "Intento de revertir una prescripcion aprobada."},
                        tolerar_error=True)
    check("La red rechaza modificar una APROBADA", codigo >= 400,
          f"HTTP {codigo} — {str(err.get('detail') or err.get('title'))[:60]}")

    # ── 5. La cadena de hashes ───────────────────────────────────────────────
    titulo("5. Verificacion de la cadena de hashes")
    _, ver = pedir(f"/api/prescriptions/{pid}/verify", tokens["auditor"])
    check("El sistema declara la cadena valida", ver.get("valido") is True, str(ver.get("errores")))

    # Verificacion INDEPENDIENTE: se recomputa el hash desde el contenido,
    # sin confiar en lo que dice el endpoint.
    _, asset = pedir(f"/api/prescriptions/{pid}", tokens["auditor"])
    recomputado = sha256_hex(build_canonical_payload(
        asset.get("clinical", {}), asset.get("ml", {}), asset.get("created_at", "")))
    check("Recomputado por fuera, coincide", recomputado == asset.get("payload_hash"),
          f"{recomputado[:20]}...")

    # ── 6. La prueba que importa: detectar adulteracion ──────────────────────
    titulo("6. Adulteracion: se detecta?")
    adulterado = json.loads(json.dumps(asset))
    original = adulterado["clinical"]["estadio"]
    adulterado["clinical"]["estadio"] = "I"          # bajar el estadio abarata el tratamiento
    hash_adulterado = sha256_hex(build_canonical_payload(
        adulterado["clinical"], adulterado["ml"], adulterado["created_at"]))
    check(f"Cambiar estadio {original}->I rompe el payload_hash",
          hash_adulterado != asset["payload_hash"], "el hash on-chain ya no reproduce")

    if asset.get("audit_events"):
        ev = json.loads(json.dumps(asset["audit_events"][0]))
        ev["justificacion"] = "Justificacion reescrita a posteriori"
        from backend.security.canonical import compute_event_hash
        rehecho = compute_event_hash(ev["prev_hash"], ev["accion"], ev["estado_resultante"],
                                     ev["auditor"], ev["justificacion"], ev["timestamp"])
        check("Reescribir una justificacion rompe su event_hash",
              rehecho != asset["audit_events"][0]["event_hash"])

    # ── 7. Control de acceso ─────────────────────────────────────────────────
    titulo("7. Control de acceso")
    codigo, _ = pedir(f"/api/audit/{pid}/accion", tokens["prescriptor"], "POST",
                      {"accion": "aprobar", "justificacion": "El prescriptor se autoaprueba."},
                      tolerar_error=True)
    check("Un prescriptor no puede auditar", codigo in (401, 403), f"HTTP {codigo}")

    codigo, _ = pedir("/api/users", tokens["prescriptor"], tolerar_error=True)
    check("Solo super_admin gestiona usuarios", codigo in (401, 403), f"HTTP {codigo}")

    # ── Resultado ────────────────────────────────────────────────────────────
    titulo(f"RESULTADO: {_ok} checks OK, {_fallos} fallan")
    print(f"  Prescripcion de prueba: {pid}")
    print(f"  Trazabilidad: {API.replace('vl5nsf5jt5.execute-api.us-east-1.amazonaws.com', '<app>')}"
          f"/trazabilidad\n")
    return 1 if _fallos else 0


if __name__ == "__main__":
    sys.exit(main())
