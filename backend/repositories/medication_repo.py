"""Repositorio de medicamentos con soporte PostgreSQL y fallback en memoria."""
import logging
from typing import List

from backend.models.medication import Medication

logger = logging.getLogger(__name__)


class MedicationRepository:
    """Repositorio de medicamentos con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        """Inicializa el almacen de medicamentos."""
        try:
            self._store: List[Medication] = []
            self._next_id = 1
        except Exception as exc:
            logger.error("Error al inicializar MedicationRepository: %s", exc, exc_info=True)
            raise

    def _db_available(self) -> bool:
        """Verifica si la base de datos esta disponible."""
        try:
            from backend.db import is_db_available
            return is_db_available()
        except Exception:
            return False

    def next_id(self) -> int:
        """Devuelve el proximo ID disponible."""
        try:
            if self._db_available():
                return 0
            current = self._next_id
            self._next_id += 1
            return current
        except Exception as exc:
            logger.error("Error al obtener next_id: %s", exc, exc_info=True)
            raise

    def add(self, medication: Medication) -> Medication:
        """Agrega un medicamento al repositorio."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("medications.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["insert_medication"],
                            (
                                medication.descripcion, medication.ean,
                                medication.codigo_alfabeta, medication.tipo_conservacion,
                                medication.sap_id, medication.monodroga_id,
                                medication.tamano_dimension,
                            ),
                        )
                        row = cur.fetchone()
                        medication = medication.model_copy(update={"id": row[0]})
                return medication
            self._store.append(medication)
            return medication
        except Exception as exc:
            logger.error("Error al agregar medicamento: %s", exc, exc_info=True)
            raise

    def list_all(self) -> List[Medication]:
        """Lista todos los medicamentos."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("medications.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_all_medications"])
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    result.append(Medication(**data))
                return result
            return list(self._store)
        except Exception as exc:
            logger.error("Error al listar medicamentos: %s", exc, exc_info=True)
            raise
