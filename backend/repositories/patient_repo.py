"""Repositorio de pacientes con soporte PostgreSQL y fallback en memoria."""
import json
import logging
from typing import List, Optional

from backend.models.patient import Patient

logger = logging.getLogger(__name__)


class PatientRepository:
    """Repositorio de pacientes con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        """Inicializa el almacen de pacientes."""
        try:
            self._store: List[Patient] = []
            self._next_id = 1
        except Exception as exc:
            logger.error("Error al inicializar PatientRepository: %s", exc, exc_info=True)
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

    def add(self, patient: Patient) -> Patient:
        """Agrega un paciente al repositorio."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("patients.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["insert_patient"],
                            (
                                patient.sap_id, patient.credential_id, patient.provider_id,
                                patient.provider, patient.first_name, patient.last_name,
                                str(patient.birth_date), patient.gender, patient.treatment,
                                json.dumps(patient.medications), patient.tipo_empadronamiento,
                                str(patient.fecha_inicio), str(patient.fecha_primera_toma),
                                patient.cadencia_estimada_toma, patient.hc_filename,
                                patient.ap_filename, patient.img_filename, patient.lab_filename,
                                patient.receta_filename, patient.otros_filename,
                                patient.blockchain_tx_id,
                            ),
                        )
                        row = cur.fetchone()
                        patient = patient.model_copy(update={"id": row[0]})
                return patient
            self._store.append(patient)
            return patient
        except Exception as exc:
            logger.error("Error al agregar paciente: %s", exc, exc_info=True)
            raise

    def list_all(self) -> List[Patient]:
        """Lista todos los pacientes."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query
                queries = load_query("patients.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_all_patients"])
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    data["medications"] = json.loads(data.get("medications") or "[]")
                    result.append(Patient(**data))
                return result
            return list(self._store)
        except Exception as exc:
            logger.error("Error al listar pacientes: %s", exc, exc_info=True)
            raise
