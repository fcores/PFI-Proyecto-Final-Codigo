"""Repositorio de monodrogas con soporte PostgreSQL y fallback en memoria."""
import logging
from typing import List, Optional

from backend.models.monodrug import Monodrug

logger = logging.getLogger(__name__)


class MonodrugRepository:
    """Repositorio de monodrogas con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        """Inicializa el almacen de monodrogas."""
        try:
            self._store: List[Monodrug] = []
            self._next_id = 1
        except Exception as exc:
            logger.error("Error al inicializar MonodrugRepository: %s", exc, exc_info=True)
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
        """Devuelve la cantidad total de monodrogas para generar el codigo."""
        try:
            if self._db_available():
                from backend.db import get_db
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT COUNT(*) FROM monodrugs")
                        return cur.fetchone()[0]
            return len(self._store)
        except Exception as exc:
            logger.error("Error al contar monodrogas: %s", exc, exc_info=True)
            raise

    def add(self, monodrug: Monodrug) -> Monodrug:
        """Agrega una monodroga al repositorio."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("monodrugs.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["insert_monodrug"],
                            (monodrug.descripcion, monodrug.codigo),
                        )
                        row = cur.fetchone()
                        monodrug = monodrug.model_copy(update={"id": row[0]})
                return monodrug
            self._store.append(monodrug)
            return monodrug
        except Exception as exc:
            logger.error("Error al agregar monodroga: %s", exc, exc_info=True)
            raise

    def list_all(self) -> List[Monodrug]:
        """Lista todas las monodrogas."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("monodrugs.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_all_monodrugs"])
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    result.append(Monodrug(**data))
                return result
            return list(self._store)
        except Exception as exc:
            logger.error("Error al listar monodrogas: %s", exc, exc_info=True)
            raise

    def find_by_descripcion(self, descripcion: str) -> Optional[Monodrug]:
        """Busca una monodroga por su descripcion (case-insensitive)."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("monodrugs.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["find_monodrug_by_descripcion"], (descripcion,))
                        columns = [desc[0] for desc in cur.description]
                        row = cur.fetchone()
                if row is None:
                    return None
                data = dict(zip(columns, row))
                return Monodrug(**data)
            for item in self._store:
                if item.descripcion.lower() == descripcion.lower():
                    return item
            return None
        except Exception as exc:
            logger.error("Error al buscar monodroga por descripcion '%s': %s", descripcion, exc, exc_info=True)
            raise
