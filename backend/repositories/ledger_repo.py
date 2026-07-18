"""Repositorio del ledger blockchain con soporte PostgreSQL y fallback en memoria."""
import json
import logging
from typing import List

from backend.models.ledger import Block

logger = logging.getLogger(__name__)


class LedgerRepository:
    """Repositorio del ledger con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        """Inicializa el almacen de bloques."""
        try:
            self._chain: List[Block] = []
        except Exception as exc:
            logger.error("Error al inicializar LedgerRepository: %s", exc, exc_info=True)
            raise

    def _db_available(self) -> bool:
        """Verifica si la base de datos esta disponible."""
        try:
            from backend.db import is_db_available
            return is_db_available()
        except Exception:
            return False

    def add(self, block: Block) -> Block:
        """Agrega un bloque al ledger."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("ledger.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["insert_block"],
                            (
                                block.index, block.timestamp, block.tx_type,
                                json.dumps(block.payload), block.prev_hash, block.hash,
                            ),
                        )
                return block
            self._chain.append(block)
            return block
        except Exception as exc:
            logger.error("Error al agregar bloque al ledger: %s", exc, exc_info=True)
            raise

    def last(self) -> Block:
        """Retorna el ultimo bloque del ledger."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("ledger.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_last_block"])
                        columns = [desc[0] for desc in cur.description]
                        row = cur.fetchone()
                if row is None:
                    raise IndexError("Ledger vacio, no hay bloques")
                data = dict(zip(columns, row))
                if isinstance(data.get("payload"), str):
                    data["payload"] = json.loads(data["payload"])
                return Block(**data)
            return self._chain[-1]
        except Exception as exc:
            logger.error("Error al obtener ultimo bloque: %s", exc, exc_info=True)
            raise

    def is_empty(self) -> bool:
        """Verifica si el ledger esta vacio."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("ledger.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["count_blocks"])
                        count = cur.fetchone()[0]
                return count == 0
            return len(self._chain) == 0
        except Exception as exc:
            logger.error("Error al verificar si ledger esta vacio: %s", exc, exc_info=True)
            raise

    def list_all(self) -> List[Block]:
        """Lista todos los bloques del ledger."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("ledger.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_all_blocks"])
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    if isinstance(data.get("payload"), str):
                        data["payload"] = json.loads(data["payload"])
                    result.append(Block(**data))
                return result
            return list(self._chain)
        except Exception as exc:
            logger.error("Error al listar bloques del ledger: %s", exc, exc_info=True)
            raise
