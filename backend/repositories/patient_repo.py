"""Repositorio de pacientes con cifrado PHI y soporte PostgreSQL."""

import json
import logging

from backend.models.patient import Patient

logger = logging.getLogger(__name__)


def _get_crypto():
    """Obtiene el servicio de cifrado (lazy import para evitar ciclos)."""
    try:
        from backend.security.key_manager import get_crypto_service

        return get_crypto_service()
    except Exception as e:
        logger.warning("CryptoService no disponible: %s", e)
        return None


class PatientRepository:
    """Repositorio de pacientes con cifrado PHI en columnas _enc."""

    def __init__(self) -> None:
        self._store: list[Patient] = []
        self._next_id = 1

    def _db_available(self) -> bool:
        from backend.db import is_db_available

        return is_db_available()

    def next_id(self) -> int:
        if self._db_available():
            return 0
        current = self._next_id
        self._next_id += 1
        return current

    def _encrypt_phi(self, patient: Patient, patient_id: int) -> dict:
        """Cifra campos PHI y genera blind indexes."""
        crypto = _get_crypto()
        if not crypto:
            return {
                "first_name_enc": None,
                "last_name_enc": None,
                "birth_date_enc": None,
                "gender_enc": None,
                "treatment_enc": None,
                "first_name_bidx": None,
                "last_name_bidx": None,
                "birth_date_bidx": None,
            }
        pid = patient_id or 0
        return {
            "first_name_enc": crypto.encrypt_field(patient.first_name, pid, "first_name"),
            "last_name_enc": crypto.encrypt_field(patient.last_name, pid, "last_name"),
            "birth_date_enc": crypto.encrypt_field(str(patient.birth_date), pid, "birth_date"),
            "gender_enc": crypto.encrypt_field(patient.gender, pid, "gender"),
            "treatment_enc": (
                crypto.encrypt_field(patient.treatment or "", pid, "treatment") if patient.treatment else None
            ),
            "first_name_bidx": crypto.blind_index(patient.first_name),
            "last_name_bidx": crypto.blind_index(patient.last_name),
            "birth_date_bidx": crypto.blind_index(str(patient.birth_date)),
        }

    def _decrypt_row(self, data: dict) -> dict:
        """Descifra campos PHI de una fila de DB. Si hay _enc, los usa; sino, usa plaintext."""
        crypto = _get_crypto()
        patient_id = data.get("id", 0)

        if crypto and data.get("first_name_enc"):
            try:
                data["first_name"] = crypto.decrypt_field(data["first_name_enc"], patient_id, "first_name")
                data["last_name"] = crypto.decrypt_field(data["last_name_enc"], patient_id, "last_name")
                if data.get("birth_date_enc"):
                    data["birth_date"] = crypto.decrypt_field(data["birth_date_enc"], patient_id, "birth_date")
                if data.get("gender_enc"):
                    data["gender"] = crypto.decrypt_field(data["gender_enc"], patient_id, "gender")
                if data.get("treatment_enc"):
                    data["treatment"] = crypto.decrypt_field(data["treatment_enc"], patient_id, "treatment")
            except Exception as e:
                logger.error("Error al descifrar paciente %s: %s", patient_id, e)

        for key in ["first_name_enc", "last_name_enc", "birth_date_enc", "gender_enc", "treatment_enc"]:
            data.pop(key, None)
        return data

    def add(self, patient: Patient) -> Patient:
        """Agrega un paciente cifrando PHI."""
        if self._db_available():
            from backend.db import get_db, load_query

            queries = load_query("patients.sql")

            enc = self._encrypt_phi(patient, patient.id or 0)

            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        queries["insert_patient"],
                        (
                            patient.credential_id,
                            patient.provider_id,
                            patient.provider,
                            patient.first_name,
                            patient.last_name,
                            str(patient.birth_date),
                            patient.gender,
                            patient.treatment,
                            json.dumps(patient.medications),
                            patient.hc_filename,
                            patient.ap_filename,
                            patient.img_filename,
                            patient.lab_filename,
                            patient.receta_filename,
                            patient.otros_filename,
                            patient.blockchain_tx_id,
                            enc["first_name_enc"],
                            enc["last_name_enc"],
                            enc["birth_date_enc"],
                            enc["gender_enc"],
                            enc["treatment_enc"],
                            enc["first_name_bidx"],
                            enc["last_name_bidx"],
                            enc["birth_date_bidx"],
                        ),
                    )
                    row = cur.fetchone()
                    new_id = row[0]

                # Re-encrypt with actual ID if we used 0
                if (patient.id or 0) == 0 and _get_crypto():
                    patient_with_id = patient.model_copy(update={"id": new_id})
                    enc2 = self._encrypt_phi(patient_with_id, new_id)
                    with conn.cursor() as cur:
                        sql = (
                            "UPDATE patients SET first_name_enc=%s, last_name_enc=%s,"
                            " birth_date_enc=%s, gender_enc=%s, treatment_enc=%s"
                            " WHERE id=%s"
                        )
                        cur.execute(
                            sql,
                            (
                                enc2["first_name_enc"],
                                enc2["last_name_enc"],
                                enc2["birth_date_enc"],
                                enc2["gender_enc"],
                                enc2["treatment_enc"],
                                new_id,
                            ),
                        )

                patient = patient.model_copy(update={"id": new_id})
            return patient
        self._store.append(patient)
        return patient

    def find_by_id(self, patient_id: int) -> Patient | None:
        """Busca un paciente por ID, descifrando PHI."""
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
                    data = self._decrypt_row(data)
                    return Patient(**data)
        for p in self._store:
            if p.id == patient_id:
                return p
        return None

    def search(self, query: str) -> list[Patient]:
        """Busca pacientes usando blind index cuando crypto esta disponible."""
        if self._db_available():
            from backend.db import get_db, load_query

            queries = load_query("patients.sql")
            crypto = _get_crypto()

            with get_db() as conn:
                with conn.cursor() as cur:
                    if crypto and "search_patients_by_index" in queries:
                        bidx = crypto.blind_index(query)
                        cur.execute(queries["search_patients_by_index"], (bidx, bidx))
                    else:
                        pattern = f"%{query.lower()}%"
                        cur.execute(queries["search_patients"], (pattern, pattern))
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
            result = []
            for row in rows:
                data = dict(zip(columns, row))
                data["medications"] = json.loads(data.get("medications") or "[]")
                data = self._decrypt_row(data)
                result.append(Patient(**data))
            return result
        q = query.lower()
        return [p for p in self._store if q in p.first_name.lower() or q in p.last_name.lower()]

    def list_all(self) -> list[Patient]:
        """Lista todos los pacientes, descifrando PHI."""
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
                data = self._decrypt_row(data)
                result.append(Patient(**data))
            return result
        return list(self._store)
