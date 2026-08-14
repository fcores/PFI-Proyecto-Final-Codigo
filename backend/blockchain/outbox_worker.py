"""
Worker del patron outbox: procesa prescripciones pendientes de commit a Fabric.

Diseñado para correr como background task o como comando CLI.
Garantiza idempotencia: un mismo prescription_id nunca se commitea dos veces
porque CreatePrescription en el chaincode rechaza claves existentes.
"""
import json
import logging
import time

from backend.blockchain.fabric_client import get_fabric_client, FabricResponse

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5
_BACKOFF_BASE = 3.0


def process_pending_outbox() -> int:
    """Procesa todas las entradas pendientes del outbox.

    Returns:
        Cantidad de entradas procesadas exitosamente.
    """
    from backend.db import get_db, is_db_available

    if not is_db_available():
        return 0

    client = get_fabric_client()
    if not client.available:
        logger.warning("Fabric client no disponible, saltando ciclo de outbox")
        return 0

    processed = 0

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, prescription_id, payload, attempts, idempotency_key
                FROM prescription_outbox
                WHERE status = 'pending' AND attempts < %s
                ORDER BY created_at
                LIMIT 10
                FOR UPDATE SKIP LOCKED
            """, (_MAX_ATTEMPTS,))
            rows = cur.fetchall()

            for row in rows:
                outbox_id, prescription_id, payload, attempts, idempotency_key = row

                response = client.invoke("CreatePrescription", [payload])

                if response.success and response.tx_id:
                    cur.execute("""
                        UPDATE prescription_outbox
                        SET status = 'committed', updated_at = NOW()
                        WHERE id = %s
                    """, (outbox_id,))
                    cur.execute("""
                        UPDATE prescriptions
                        SET estado_commit = 'confirmado',
                            tx_id = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (response.tx_id, prescription_id))
                    processed += 1
                    logger.info(
                        "Prescription %d committed a Fabric (tx: %s)",
                        prescription_id, response.tx_id,
                    )
                else:
                    error_msg = response.error or "Error desconocido"
                    # Si es error de idempotencia, marcar como committed
                    if "ya existe" in error_msg:
                        cur.execute("""
                            UPDATE prescription_outbox
                            SET status = 'committed', updated_at = NOW()
                            WHERE id = %s
                        """, (outbox_id,))
                        cur.execute("""
                            UPDATE prescriptions
                            SET estado_commit = 'confirmado', updated_at = NOW()
                            WHERE id = %s
                        """, (prescription_id,))
                        processed += 1
                    else:
                        new_attempts = attempts + 1
                        new_status = "failed" if new_attempts >= _MAX_ATTEMPTS else "pending"
                        cur.execute("""
                            UPDATE prescription_outbox
                            SET status = %s, attempts = %s, last_error = %s, updated_at = NOW()
                            WHERE id = %s
                        """, (new_status, new_attempts, error_msg, outbox_id))

                        if new_status == "failed":
                            cur.execute("""
                                UPDATE prescriptions
                                SET estado_commit = 'fallido', updated_at = NOW()
                                WHERE id = %s
                            """, (prescription_id,))
                            logger.error(
                                "Prescription %d: commit fallido definitivamente tras %d intentos",
                                prescription_id, new_attempts,
                            )

    return processed


def run_outbox_loop(interval_seconds: float = 10.0) -> None:
    """Loop infinito que procesa el outbox cada N segundos."""
    logger.info("Outbox worker iniciado (intervalo: %.1fs)", interval_seconds)
    while True:
        try:
            count = process_pending_outbox()
            if count > 0:
                logger.info("Outbox: %d prescripciones committeadas", count)
        except Exception as exc:
            logger.error("Error en ciclo de outbox: %s", exc, exc_info=True)
        time.sleep(interval_seconds)
