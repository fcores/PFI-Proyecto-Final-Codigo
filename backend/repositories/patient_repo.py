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


def _load_medications(valor) -> list:
    """Normaliza patients.medications a lista.

    La migracion 005 pasa la columna de TEXT a JSONB: desde entonces psycopg2
    devuelve una lista/dict ya deserializado en vez de un str, y aplicarle
    json.loads revienta con "the JSON object must be str, bytes or bytearray".
    Se aceptan los dos formatos para que el repo funcione contra una base
    migrada y contra una que todavia no lo esta.
    """
    if valor is None or valor == "":
        return []
    if isinstance(valor, list):
        return valor
    if isinstance(valor, dict):
        return [valor]
    try:
        cargado = json.loads(valor)
    except (TypeError, ValueError):
        logger.warning("medications con formato inesperado: %r", valor)
        return []
    return cargado if isinstance(cargado, list) else [cargado]


class PatientRepository:
    """Repositorio de pacientes con cifrado PHI en columnas _enc."""

    def __init__(self) -> None:
        self._store: list[Patient] = []
        self._next_id = 1

    def _db_available(self) -> bool:
        from backend.db import is_db_available

        return is_db_available()

    def _log_phi_access(
        self,
        patient_ids: list[int],
        action: str,
        fields_accessed: str,
        user_id: int = 0,
        username: str = "system",
    ) -> None:
        """Registra accesos a datos PHI en phi_access_log (Ley 25.326 / habeas data)."""
        if not self._db_available() or not patient_ids:
            return
        try:
            from backend.db import get_db, load_query

            queries = load_query("patients.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    for pid in patient_ids:
                        cur.execute(
                            queries["insert_phi_access_log"],
                            (user_id, username, pid, action, fields_accessed),
                        )
        except Exception as e:
            logger.warning("No se pudo registrar acceso PHI: %s", e)

    def next_id(self) -> int:
        if self._db_available():
            return 0
        current = self._next_id
        self._next_id += 1
        return current

    def _encrypt_phi(self, patient: Patient, patient_id: int) -> dict:
        """Cifra todos los campos PHI y genera blind indexes."""
        crypto = _get_crypto()
        if not crypto:
            return {
                "first_name_enc": None,
                "last_name_enc": None,
                "birth_date_enc": None,
                "gender_enc": None,
                "provider_enc": None,
                "provider_id_enc": None,
                "credential_id_enc": None,
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
            "provider_enc": (
                crypto.encrypt_field(patient.provider or "", pid, "provider") if patient.provider else None
            ),
            "provider_id_enc": (
                crypto.encrypt_field(patient.provider_id or "", pid, "provider_id") if patient.provider_id else None
            ),
            "credential_id_enc": (
                crypto.encrypt_field(patient.credential_id or "", pid, "credential_id")
                if patient.credential_id
                else None
            ),
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
                if data.get("provider_enc"):
                    data["provider"] = crypto.decrypt_field(data["provider_enc"], patient_id, "provider")
                if data.get("provider_id_enc"):
                    data["provider_id"] = crypto.decrypt_field(data["provider_id_enc"], patient_id, "provider_id")
                if data.get("credential_id_enc"):
                    data["credential_id"] = crypto.decrypt_field(data["credential_id_enc"], patient_id, "credential_id")
                if data.get("treatment_enc"):
                    data["treatment"] = crypto.decrypt_field(data["treatment_enc"], patient_id, "treatment")
            except Exception as e:
                logger.error("Error al descifrar paciente %s: %s", patient_id, e)

        _enc_keys = [
            "first_name_enc",
            "last_name_enc",
            "birth_date_enc",
            "gender_enc",
            "provider_enc",
            "provider_id_enc",
            "credential_id_enc",
            "treatment_enc",
        ]
        for key in _enc_keys:
            data.pop(key, None)
        return data

    def _populate_name_tokens(self, patient_id: int, first_name: str, last_name: str) -> None:
        """Genera tokens de nombre/apellido para busqueda por palabra suelta."""
        crypto = _get_crypto()
        if not crypto or not self._db_available():
            return
        try:
            from backend.db import get_db, load_query

            queries = load_query("patients.sql")
            tokens = set()
            for part in (first_name, last_name):
                for word in part.strip().split():
                    word = word.strip()
                    if word:
                        tokens.add(crypto.blind_index_token(word))
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["delete_name_tokens"], (patient_id,))
                    for tok in tokens:
                        cur.execute(queries["insert_name_token"], (patient_id, tok))
        except Exception as e:
            logger.warning("No se pudieron poblar name_tokens para paciente %s: %s", patient_id, e)

    def add(self, patient: Patient) -> Patient:
        """Agrega un paciente cifrando PHI."""
        if self._db_available():
            import psycopg2

            from backend.db import get_db, load_query
            from backend.error_handlers import ConflictError

            queries = load_query("patients.sql")

            enc = self._encrypt_phi(patient, patient.id or 0)

            try:
                saved = self._insert(patient, enc, queries, get_db)
                self._populate_name_tokens(saved.id, patient.first_name, patient.last_name)
                return saved
            except psycopg2.errors.UniqueViolation as exc:
                logger.warning("Paciente duplicado rechazado por la base: %s", exc)
                raise ConflictError("Ya existe un paciente con ese nombre, apellido y fecha de nacimiento.") from exc
        self._store.append(patient)
        return patient

    def _insert(self, patient: Patient, enc: dict, queries: dict, get_db) -> Patient:
        """Ejecuta el INSERT del paciente y el re-cifrado con el ID real.

        Plaintext PHI columns receive redacted placeholders ('***') when
        encryption is active so that the cleartext never persists at rest.
        """
        crypto_active = _get_crypto() is not None
        redacted = "***"
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    queries["insert_patient"],
                    (
                        redacted if crypto_active else patient.credential_id,
                        redacted if crypto_active else patient.provider_id,
                        redacted if crypto_active else patient.provider,
                        redacted if crypto_active else patient.first_name,
                        redacted if crypto_active else patient.last_name,
                        str(patient.birth_date),
                        redacted if crypto_active else patient.gender,
                        redacted if crypto_active else patient.treatment,
                        json.dumps(patient.medications),
                        patient.hc_filename,
                        patient.ap_filename,
                        patient.img_filename,
                        patient.lab_filename,
                        patient.receta_filename,
                        patient.otros_filename,
                        enc["first_name_enc"],
                        enc["last_name_enc"],
                        enc["birth_date_enc"],
                        enc["gender_enc"],
                        enc["provider_enc"],
                        enc["provider_id_enc"],
                        enc["credential_id_enc"],
                        enc["treatment_enc"],
                        enc["first_name_bidx"],
                        enc["last_name_bidx"],
                        enc["birth_date_bidx"],
                    ),
                )
                row = cur.fetchone()
                new_id = row[0]

            if (patient.id or 0) == 0 and crypto_active:
                patient_with_id = patient.model_copy(update={"id": new_id})
                enc2 = self._encrypt_phi(patient_with_id, new_id)
                with conn.cursor() as cur:
                    sql = (
                        "UPDATE patients SET first_name_enc=%s, last_name_enc=%s,"
                        " birth_date_enc=%s, gender_enc=%s, provider_enc=%s,"
                        " provider_id_enc=%s, credential_id_enc=%s, treatment_enc=%s"
                        " WHERE id=%s"
                    )
                    cur.execute(
                        sql,
                        (
                            enc2["first_name_enc"],
                            enc2["last_name_enc"],
                            enc2["birth_date_enc"],
                            enc2["gender_enc"],
                            enc2["provider_enc"],
                            enc2["provider_id_enc"],
                            enc2["credential_id_enc"],
                            enc2["treatment_enc"],
                            new_id,
                        ),
                    )

            patient = patient.model_copy(update={"id": new_id})
        return patient

    def find_by_id(self, patient_id: int, user_id: int = 0, username: str = "system") -> Patient | None:
        """Busca un paciente por ID, descifrando PHI y registrando el acceso."""
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
                    data["medications"] = _load_medications(data.get("medications"))
                    data = self._decrypt_row(data)
                    self._log_phi_access([patient_id], "read", "all_phi", user_id, username)
                    return Patient(**data)
        for p in self._store:
            if p.id == patient_id:
                return p
        return None

    def search(self, query: str, user_id: int = 0, username: str = "system") -> list[Patient]:
        """Busca pacientes usando blind index (exacto) o token search (por palabra)."""
        if self._db_available():
            from backend.db import get_db, load_query

            queries = load_query("patients.sql")
            crypto = _get_crypto()

            with get_db() as conn:
                with conn.cursor() as cur:
                    if crypto and "search_patients_by_index" in queries:
                        bidx = crypto.blind_index(query)
                        cur.execute(queries["search_patients_by_index"], (bidx, bidx))
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                        if not rows and "search_patients_by_token" in queries:
                            token_bidx = crypto.blind_index_token(query)
                            cur.execute(queries["search_patients_by_token"], (token_bidx,))
                            columns = [desc[0] for desc in cur.description]
                            rows = cur.fetchall()
                    else:
                        pattern = f"%{query.lower()}%"
                        cur.execute(queries["search_patients"], (pattern, pattern))
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
            result = []
            for row in rows:
                data = dict(zip(columns, row))
                data["medications"] = _load_medications(data.get("medications"))
                data = self._decrypt_row(data)
                result.append(Patient(**data))
            if result:
                self._log_phi_access(
                    [p.id for p in result],
                    "search",
                    "all_phi",
                    user_id,
                    username,
                )
            return result
        q = query.lower()
        return [p for p in self._store if q in p.first_name.lower() or q in p.last_name.lower()]

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: int = 0,
        username: str = "system",
    ) -> list[Patient]:
        """Lista pacientes con paginacion, descifrando PHI y registrando acceso."""
        if self._db_available():
            from backend.db import get_db, load_query

            queries = load_query("patients.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["select_all_patients"], (limit, offset))
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
            result = []
            for row in rows:
                data = dict(zip(columns, row))
                data["medications"] = _load_medications(data.get("medications"))
                data = self._decrypt_row(data)
                result.append(Patient(**data))
            if result:
                self._log_phi_access(
                    [p.id for p in result],
                    "list_all",
                    "all_phi",
                    user_id,
                    username,
                )
            return result
        return list(self._store[offset : offset + limit])
