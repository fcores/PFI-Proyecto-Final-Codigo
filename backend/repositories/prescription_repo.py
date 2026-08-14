"""Repositorio de prescripciones con soporte PostgreSQL y fallback en memoria."""
import json
import logging
from typing import List

from backend.models.prescription import (
    DosisFarmaco,
    FeatureAporte,
    Prescription,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class PrescriptionRepository:
    """Repositorio de prescripciones con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        self._store: List[Prescription] = []
        self._next_id = 1

    def _db_available(self) -> bool:
        from backend.db import is_db_available
        return is_db_available()

    def next_id(self) -> int:
        """Devuelve el proximo ID disponible.
        En modo DB usa la secuencia prescription_id_seq para evitar PRESC-0000.
        """
        if self._db_available():
            from backend.db import get_db, load_query
            queries = load_query("prescriptions.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["next_prescription_id"])
                    row = cur.fetchone()
                    return row[0]
        current = self._next_id
        self._next_id += 1
        return current

    def _features_to_json(self, features):
        payload = []
        for item in features or []:
            if hasattr(item, "model_dump"):
                payload.append(item.model_dump())
            else:
                payload.append(item)
        return json.dumps(payload)

    def _dosis_to_json(self, dosis_por_farmaco):
        payload = []
        for item in dosis_por_farmaco or []:
            if hasattr(item, "model_dump"):
                payload.append(item.model_dump())
            else:
                payload.append(item)
        return json.dumps(payload)

    def _row_to_prescription(self, data):
        """Mapea una fila de DB a Prescription."""
        dosis_raw = json.loads(data.pop("dosis_por_farmaco", "[]") or "[]")
        dosis = [DosisFarmaco(**item) for item in dosis_raw]

        features_raw = json.loads(data.pop("features_relevantes", "[]") or "[]")
        features = [FeatureAporte(**item) for item in features_raw]

        validacion = ValidationResult(
            estado=data.pop("estado_validacion", ""),
            motivos=json.loads(data.pop("motivos_validacion", "[]") or "[]"),
            probabilidad_concordante=data.pop("probabilidad_concordante", None),
            nivel_confianza=data.pop("nivel_confianza", None),
            umbral_bajo=data.pop("umbral_bajo", None),
            umbral_alto=data.pop("umbral_alto", None),
            origen=data.pop("origen_validacion", None),
            version_modelo=data.pop("version_modelo", None),
            features_relevantes=features,
        )
        data["dosis_por_farmaco"] = dosis
        data["validacion"] = validacion
        return Prescription(**data)

    def add(self, prescription: Prescription) -> Prescription:
        """Agrega una prescripcion al repositorio."""
        if self._db_available():
            from backend.db import get_db, load_query
            queries = load_query("prescriptions.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        queries["insert_prescription"],
                        (
                            prescription.prescription_code,
                            prescription.patient_id,
                            prescription.edad,
                            prescription.sexo,
                            prescription.peso_kg,
                            prescription.talla_cm,
                            prescription.superficie_corporal_m2,
                            prescription.diagnostico_cie10,
                            prescription.localizacion_tumor,
                            prescription.tipo_histologico,
                            prescription.t,
                            prescription.n,
                            prescription.m,
                            prescription.estadio,
                            prescription.msi,
                            prescription.ras,
                            prescription.braf_v600e,
                            prescription.linea_tratamiento,
                            prescription.id_regimen,
                            prescription.esquema,
                            self._dosis_to_json(prescription.dosis_por_farmaco),
                            prescription.dosis_mg_m2,
                            prescription.medico_prescriptor,
                            prescription.matricula,
                            prescription.validacion.estado,
                            json.dumps(prescription.validacion.motivos),
                            prescription.validacion.probabilidad_concordante,
                            prescription.validacion.nivel_confianza,
                            prescription.validacion.umbral_bajo,
                            prescription.validacion.umbral_alto,
                            prescription.validacion.origen,
                            prescription.validacion.version_modelo,
                            self._features_to_json(prescription.validacion.features_relevantes),
                            prescription.blockchain_tx_id,
                            prescription.block_index,
                        ),
                    )
                    row = cur.fetchone()
                    prescription = prescription.model_copy(update={"id": row[0]})
            return prescription
        self._store.append(prescription)
        return prescription

    def list_all(self) -> List[Prescription]:
        """Lista todas las prescripciones."""
        if self._db_available():
            from backend.db import get_db, load_query
            queries = load_query("prescriptions.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["select_all_prescriptions"])
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
            result = []
            for row in rows:
                data = dict(zip(columns, row))
                result.append(self._row_to_prescription(data))
            return result
        return list(self._store)
