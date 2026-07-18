"""Repositorio de prescripciones con soporte PostgreSQL y fallback en memoria."""
import json
import logging
from typing import List, Optional

from backend.models.prescription import Prescription

logger = logging.getLogger(__name__)


class PrescriptionRepository:
    """Repositorio de prescripciones con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        """Inicializa el almacen de prescripciones."""
        try:
            self._store: List[Prescription] = []
            self._next_id = 1
        except Exception as exc:
            logger.error("Error al inicializar PrescriptionRepository: %s", exc, exc_info=True)
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

    def add(self, prescription: Prescription) -> Prescription:
        """Agrega una prescripcion al repositorio."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("prescriptions.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["insert_prescription"],
                            (
                                prescription.prescription_code, prescription.patient_sap_id,
                                prescription.edad, prescription.sexo, prescription.peso_kg,
                                prescription.talla_cm, prescription.superficie_corporal_m2,
                                prescription.diagnostico_cie10, prescription.localizacion_tumor,
                                prescription.tipo_histologico, prescription.t, prescription.n,
                                prescription.m, prescription.estadio, prescription.msi_alta,
                                prescription.ras_mutado, prescription.braf_v600e,
                                prescription.linea_tratamiento, prescription.esquema,
                                prescription.dosis_mg_m2, prescription.medico_prescriptor,
                                prescription.matricula, prescription.validacion.estado,
                                json.dumps(prescription.validacion.motivos),
                                prescription.blockchain_tx_id, prescription.block_index,
                            ),
                        )
                        row = cur.fetchone()
                        prescription = prescription.model_copy(update={"id": row[0]})
                return prescription
            self._store.append(prescription)
            return prescription
        except Exception as exc:
            logger.error("Error al agregar prescripcion: %s", exc, exc_info=True)
            raise

    def list_all(self) -> List[Prescription]:
        """Lista todas las prescripciones."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                from backend.models.prescription import ValidationResult
                queries = load_query("prescriptions.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_all_prescriptions"])
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    data["validacion"] = ValidationResult(
                        estado=data.pop("estado_validacion", ""),
                        motivos=json.loads(data.pop("motivos_validacion", "[]") or "[]"),
                    )
                    result.append(Prescription(**data))
                return result
            return list(self._store)
        except Exception as exc:
            logger.error("Error al listar prescripciones: %s", exc, exc_info=True)
            raise

    def find_by_id(self, prescription_id: int) -> Optional[Prescription]:
        """Busca una prescripcion por su ID."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                from backend.models.prescription import ValidationResult
                queries = load_query("prescriptions.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["find_prescription_by_id"], (prescription_id,))
                        columns = [desc[0] for desc in cur.description]
                        row = cur.fetchone()
                if row is None:
                    return None
                data = dict(zip(columns, row))
                data["validacion"] = ValidationResult(
                    estado=data.pop("estado_validacion", ""),
                    motivos=json.loads(data.pop("motivos_validacion", "[]") or "[]"),
                )
                return Prescription(**data)
            for item in self._store:
                if item.id == prescription_id:
                    return item
            return None
        except Exception as exc:
            logger.error("Error al buscar prescripcion por id %s: %s", prescription_id, exc, exc_info=True)
            raise

    def update_validation(self, prescription_id: int, estado: str, motivos: List[str]) -> None:
        """Actualiza el estado de validacion de una prescripcion."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("prescriptions.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["update_prescription_validation"],
                            (estado, json.dumps(motivos), prescription_id),
                        )
                return
            for item in self._store:
                if item.id == prescription_id:
                    item.validacion.estado = estado
                    item.validacion.motivos = motivos
                    break
        except Exception as exc:
            logger.error("Error al actualizar validacion de prescripcion %s: %s", prescription_id, exc, exc_info=True)
            raise
