"""Repositorio de medicamentos con soporte PostgreSQL y fallback en memoria."""

import logging

from backend.models.medication import Medication

logger = logging.getLogger(__name__)


class MedicationRepository:
    """Repositorio de medicamentos con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        """Inicializa el almacen de medicamentos."""
        try:
            self._store: list[Medication] = []
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

    def count(self) -> int:
        """Devuelve la cantidad total de medicamentos para generar el codigo."""
        try:
            if self._db_available():
                from backend.db import get_db

                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT COUNT(*) FROM medications")
                        return cur.fetchone()[0]
            return len(self._store)
        except Exception as exc:
            logger.error("Error al contar medicamentos: %s", exc, exc_info=True)
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
                                medication.codigo,
                                medication.descripcion,
                                medication.ean,
                                medication.codigo_alfabeta,
                                medication.tipo_conservacion,
                                medication.laboratorio,
                                medication.monodroga,
                                medication.tamano_dimension,
                                medication.potencia_mg,
                                medication.unidad_potencia,
                                medication.precio,
                                medication.via_administracion,
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

    def list_all(self) -> list[Medication]:
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

    def find_by_monodroga(self, monodroga: str) -> list[Medication]:
        """Lista presentaciones filtradas por monodroga, ordenadas por potencia."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("medications.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["select_medications_by_monodroga"],
                            (monodroga,),
                        )
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    result.append(Medication(**data))
                return result

            filtrados = []
            for med in self._store:
                if str(med.monodroga).lower() == str(monodroga).lower():
                    filtrados.append(med)
            filtrados.sort(key=lambda m: (m.potencia_mg is None, m.potencia_mg or 0, m.id))
            return filtrados
        except Exception as exc:
            logger.error(
                "Error al buscar medicamentos por monodroga %s: %s",
                monodroga,
                exc,
                exc_info=True,
            )
            raise
