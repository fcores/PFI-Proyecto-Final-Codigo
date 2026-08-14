"""Repositorio de pacientes con soporte PostgreSQL y fallback en memoria."""
import json
import logging
from typing import List, Optional

from backend.models.patient import Patient

logger = logging.getLogger(__name__)


class PatientRepository:
    """Repositorio de pacientes con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        self._store: List[Patient] = []
        self._next_id = 1

    def _db_available(self) -> bool:
        from backend.db import is_db_available
        return is_db_available()

    def next_id(self) -> int:
        """Devuelve el proximo ID disponible (solo para modo in-memory)."""
        if self._db_available():
            return 0
        current = self._next_id
        self._next_id += 1
        return current

    def add(self, patient: Patient) -> Patient:
        """Agrega un paciente al repositorio."""
        if self._db_available():
            from backend.db import get_db, load_query
            queries = load_query("patients.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        queries["insert_patient"],
                        (
                            patient.credential_id, patient.provider_id,
                            patient.provider, patient.first_name, patient.last_name,
                            str(patient.birth_date), patient.gender, patient.treatment,
                            json.dumps(patient.medications),
                            patient.hc_filename, patient.ap_filename,
                            patient.img_filename, patient.lab_filename,
                            patient.receta_filename, patient.otros_filename,
                            patient.blockchain_tx_id,
                        ),
                    )
                    row = cur.fetchone()
                    patient = patient.model_copy(update={"id": row[0]})
            return patient
        self._store.append(patient)
        return patient

    def find_by_id(self, patient_id: int) -> Optional[Patient]:
        """Busca un paciente por ID."""
        if self._db_available():
            from backend.db import get_db, load_query
            queries = load_query("patients.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["find_patient_by_id"], (patient_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    columns = [desc[0] for desc in cur.description]
                    data = dict(zip(columns, row))
                    data["medications"] = json.loads(data.get("medications") or "[]")
                    return Patient(**data)
        for p in self._store:
            if p.id == patient_id:
                return p
        return None

    def search(self, query: str) -> List[Patient]:
        """Busca pacientes por nombre o apellido (case-insensitive, substring)."""
        if self._db_available():
            from backend.db import get_db, load_query
            queries = load_query("patients.sql")
            pattern = f"%{query.lower()}%"
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["search_patients"], (pattern, pattern))
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
            result = []
            for row in rows:
                data = dict(zip(columns, row))
                data["medications"] = json.loads(data.get("medications") or "[]")
                result.append(Patient(**data))
            return result
        q = query.lower()
        return [
            p for p in self._store
            if q in p.first_name.lower() or q in p.last_name.lower()
        ]

    def list_all(self) -> List[Patient]:
        """Lista todos los pacientes."""
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
