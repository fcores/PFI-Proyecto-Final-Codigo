"""
Worker del patron outbox: procesa prescripciones pendientes de commit a Fabric.

Diseñado para correr como background task o como comando CLI.
Garantiza idempotencia: un mismo prescription_id nunca se commitea dos veces
porque CreatePrescription en el chaincode rechaza claves existentes.
"""

import logging
import time

from backend.blockchain.fabric_client import get_fabric_client

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5
_BATCH_SIZE = 10
# Una fila en 'processing' mas vieja que esto quedo huerfana (worker caido a
# mitad de un ciclo) y vuelve a la cola.
_STALE_PROCESSING_MINUTES = 15


def _reclaim_stale(cur) -> None:
    """Devuelve a 'pending' las filas que quedaron trabadas en 'processing'."""
    cur.execute(
        """
        UPDATE prescription_outbox
        SET status = 'pending', updated_at = NOW()
        WHERE status = 'processing'
          AND updated_at < NOW() - (%s * INTERVAL '1 minute')
    """,
        (_STALE_PROCESSING_MINUTES,),
    )


def _claim_batch(conn) -> list:
    """Reserva un lote de entradas pendientes marcandolas como 'processing'.

    Transaccion corta a proposito: los locks se liberan antes de llamar a
    Fabric, que puede tardar decenas de segundos por fila.
    """
    with conn.cursor() as cur:
        _reclaim_stale(cur)
        cur.execute(
            """
            SELECT id, prescription_id, payload, attempts
            FROM prescription_outbox
            WHERE status = 'pending' AND attempts < %s
            ORDER BY created_at
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """,
            (_MAX_ATTEMPTS, _BATCH_SIZE),
        )
        rows = cur.fetchall()
        if rows:
            cur.execute(
                """
                UPDATE prescription_outbox
                SET status = 'processing', updated_at = NOW()
                WHERE id = ANY(%s)
            """,
                ([r[0] for r in rows],),
            )
        return rows


def _record_success(conn, outbox_id: int, prescription_id: int, tx_id: str | None) -> None:
    """Marca la entrada como committeada y confirma la prescripcion."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE prescription_outbox SET status = 'committed', updated_at = NOW() WHERE id = %s",
            (outbox_id,),
        )
        if tx_id:
            cur.execute(
                """
                UPDATE prescriptions
                SET estado_commit = 'confirmado', tx_id = %s, updated_at = NOW()
                WHERE id = %s
            """,
                (tx_id, prescription_id),
            )
        else:
            cur.execute(
                """
                UPDATE prescriptions
                SET estado_commit = 'confirmado', updated_at = NOW()
                WHERE id = %s
            """,
                (prescription_id,),
            )


def _record_failure(conn, outbox_id: int, prescription_id: int, attempts: int, error_msg: str) -> None:
    """Contabiliza el intento fallido y marca la prescripcion si se agotaron."""
    new_attempts = attempts + 1
    new_status = "failed" if new_attempts >= _MAX_ATTEMPTS else "pending"
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE prescription_outbox
            SET status = %s, attempts = %s, last_error = %s, updated_at = NOW()
            WHERE id = %s
        """,
            (new_status, new_attempts, error_msg, outbox_id),
        )
        if new_status == "failed":
            cur.execute(
                """
                UPDATE prescriptions
                SET estado_commit = 'fallido', updated_at = NOW()
                WHERE id = %s
            """,
                (prescription_id,),
            )
            logger.error(
                "Prescription %d: commit fallido definitivamente tras %d intentos",
                prescription_id,
                new_attempts,
            )


def process_pending_outbox() -> int:
    """Procesa todas las entradas pendientes del outbox.

    Las llamadas a Fabric se hacen FUERA de transaccion: primero se reserva el
    lote (transaccion corta), despues se invoca el chaincode, y por ultimo se
    registra el resultado de cada fila (transaccion corta). Mantener los locks
    durante el HTTP a Fabric bloquearia la tabla por minutos.

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

    with get_db() as conn:
        rows = _claim_batch(conn)

    if not rows:
        return 0

    processed = 0
    for outbox_id, prescription_id, payload, attempts in rows:
        try:
            response = client.invoke("CreatePrescription", [payload])
        except Exception as exc:
            logger.error("Error invocando Fabric para outbox %d: %s", outbox_id, exc, exc_info=True)
            with get_db() as conn:
                _record_failure(conn, outbox_id, prescription_id, attempts, str(exc))
            continue

        error_msg = response.error or "Error desconocido"
        # "ya existe" es la respuesta idempotente del chaincode: la prescripcion
        # ya esta en el ledger, asi que cuenta como exito.
        if (response.success and response.tx_id) or "ya existe" in error_msg:
            tx_id = response.tx_id if response.success else None
            with get_db() as conn:
                _record_success(conn, outbox_id, prescription_id, tx_id)
            processed += 1
            logger.info("Prescription %d committed a Fabric (tx: %s)", prescription_id, tx_id)
        else:
            with get_db() as conn:
                _record_failure(conn, outbox_id, prescription_id, attempts, error_msg)

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
