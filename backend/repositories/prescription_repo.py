"""Repositorio de prescripciones con soporte PostgreSQL y fallback en memoria."""

import json
import logging

from backend.models.prescription import (
    CostoFarmaco,
    DosisFarmaco,
    FeatureAporte,
    Prescription,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class PrescriptionRepository:
    """Repositorio de prescripciones con soporte PostgreSQL y fallback en memoria."""

    def __init__(self) -> None:
        self._store: list[Prescription] = []
        self._next_id = 1

    def _db_available(self) -> bool:
        from backend.db import is_db_available

        return is_db_available()

    def _models_to_json(self, items):
        """Serializa una lista de modelos (o dicts) a JSON para columnas TEXT."""
        payload = []
        for item in items or []:
            if hasattr(item, "model_dump"):
                payload.append(item.model_dump())
            else:
                payload.append(item)
        return json.dumps(payload)

    def _features_to_json(self, features):
        return self._models_to_json(features)

    def _dosis_to_json(self, dosis_por_farmaco):
        return self._models_to_json(dosis_por_farmaco)

    def _row_to_prescription(self, data):
        """Mapea una fila de DB a Prescription."""
        dosis_raw = json.loads(data.pop("dosis_por_farmaco", "[]") or "[]")
        dosis = [DosisFarmaco(**item) for item in dosis_raw]

        features_raw = json.loads(data.pop("features_relevantes", "[]") or "[]")
        features = [FeatureAporte(**item) for item in features_raw]

        costos_raw = json.loads(data.pop("costo_por_farmaco", "[]") or "[]")
        costos = [CostoFarmaco(**item) for item in costos_raw]

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
            costo_por_farmaco=costos,
            costo_total=data.pop("costo_total", None),
        )
        data["dosis_por_farmaco"] = dosis
        data["validacion"] = validacion
        return Prescription(**data)

    def add(self, prescription: Prescription) -> Prescription:
        """Agrega una prescripcion al repositorio y devuelve la instancia con el ID real."""
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
                            self._models_to_json(prescription.validacion.costo_por_farmaco),
                            prescription.validacion.costo_total,
                            prescription.blockchain_tx_id,
                            prescription.block_index,
                        ),
                    )
                    row = cur.fetchone()
                    new_id = row[0]
                    prescription = prescription.model_copy(update={"id": new_id})
            return prescription
        if prescription.id == 0:
            prescription = prescription.model_copy(update={"id": self._next_id})
            self._next_id += 1
        self._store.append(prescription)
        return prescription

    def update_code(self, prescription_id: int, new_code: str) -> None:
        """Actualiza el prescription_code despues de conocer el ID real."""
        if self._db_available():
            from backend.db import get_db

            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE prescriptions SET prescription_code = %s WHERE id = %s",
                        (new_code, prescription_id),
                    )
        else:
            for p in self._store:
                if p.id == prescription_id:
                    idx = self._store.index(p)
                    self._store[idx] = p.model_copy(update={"prescription_code": new_code})
                    break

    def enqueue_outbox(self, prescription_id: int, payload: str) -> None:
        """Encola una entrada en el outbox para commit a Fabric."""
        if not self._db_available():
            return
        from backend.db import get_db, load_query

        queries = load_query("prescriptions.sql")
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    queries["insert_outbox"],
                    (prescription_id, "presc:%d" % prescription_id, payload),
                )

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Prescription]:
        """Lista prescripciones con paginacion."""
        if self._db_available():
            from backend.db import get_db, load_query

            queries = load_query("prescriptions.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["select_all_prescriptions"], (limit, offset))
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
            result = []
            for row in rows:
                data = dict(zip(columns, row))
                result.append(self._row_to_prescription(data))
            return result
        return list(self._store[offset : offset + limit])
