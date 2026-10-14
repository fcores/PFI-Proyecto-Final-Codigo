"""Servicio de gestion de prescripciones medicas 100% on-chain.

Flujo de alta (sincrono, dentro del request):
  1. Deriva BSA (Mosteller), esquema y dosis por defecto.
  2. Ejecuta la validacion hibrida reglas + ML (soporte de decision).
  3. Genera el ID (ULID) y arma el payload canonico {clinical, created_at, ml}.
  4. Invoca CreatePrescription en Fabric (firma PrescriptorMSP, endorsement de
     las 3 orgs). Si la red no responde, el alta falla con 503: NO hay copia
     off-chain ni cola de reintentos.

Toda prescripcion nace en estado PENDIENTE_AUDITORIA; solo el auditor cierra
el ciclo (ver AuditService).
"""

# Annotations diferidas: la clase define un metodo `list` que ensombrece al
# builtin dentro del cuerpo de la clase.
from __future__ import annotations

import logging
import math
from datetime import UTC, datetime

from ulid import ULID

from backend.blockchain.fabric_client import FabricBusinessError
from backend.error_handlers import DomainError, NotFoundError
from backend.ml.regimenes import nombre_regimen
from backend.models.prescription import (
    ClinicalData,
    Prescription,
    PrescriptionBase,
    PrescriptionList,
    VerifyResult,
)
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import build_canonical_payload, verify_chain
from backend.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


def _asset_to_prescription(asset: dict, tx_id: str | None = None) -> Prescription:
    """Convierte el asset JSON del chaincode al modelo de dominio."""
    data = dict(asset)
    data.pop("docType", None)
    if tx_id:
        data["tx_id"] = tx_id
    return Prescription(**data)


def _paged_to_list(paged: dict) -> PrescriptionList:
    return PrescriptionList(
        prescriptions=[_asset_to_prescription(item) for item in paged["items"]],
        bookmark=paged["bookmark"] or None,
        fetched_count=paged["fetched_count"],
    )


class PrescriptionService:
    """Servicio de gestion de prescripciones medicas."""

    def __init__(
        self,
        fabric_repo: FabricPrescriptionRepository,
        validation_service: ValidationService,
        dosis_service=None,
        patient_service=None,
    ) -> None:
        self._repo = fabric_repo
        self._validation_service = validation_service
        self._dosis_service = dosis_service
        self._patient_service = patient_service

    def _body_surface_area(self, peso_kg: float, talla_cm: float) -> float:
        """Calcula la superficie corporal con la formula de Mosteller."""
        return round(math.sqrt((talla_cm * peso_kg) / 3600.0), 2)

    def _derivar_dosis_mg_m2(self, data: PrescriptionBase, superficie: float) -> float:
        """Deriva un valor representativo de dosis_mg_m2 para compatibilidad."""
        if data.dosis_mg_m2 is not None and data.dosis_mg_m2 > 0:
            return float(data.dosis_mg_m2)
        if data.dosis_por_farmaco and superficie > 0:
            total = sum(float(item.dosis_mg) for item in data.dosis_por_farmaco)
            if total > 0:
                return round(total / superficie, 2)
        return 0.01

    def _asegurar_esquema(self, data: PrescriptionBase) -> str:
        """Completa el esquema legible a partir del regimen si falta."""
        if data.esquema and str(data.esquema).strip():
            return data.esquema
        return nombre_regimen(data.id_regimen)

    def create(self, data: PrescriptionBase, prescriptor_username: str | None = None) -> Prescription:
        """Crea una prescripcion: valida con el motor hibrido y la asienta en Fabric.

        prescriptor_username es el usuario autenticado que la registra; queda en
        el bloque clinico on-chain.
        """
        try:
            # El asset es inmutable: una prescripcion sobre un paciente
            # inexistente no podria corregirse despues.
            if self._patient_service is not None and not self._patient_service.exists(data.patient_id):
                raise DomainError(
                    f"El paciente {data.patient_id} no existe en el padron.",
                    status_code=422,
                    error_type="validation_error",
                )

            superficie = self._body_surface_area(data.peso_kg, data.talla_cm)
            esquema = self._asegurar_esquema(data)
            dosis_mg_m2 = self._derivar_dosis_mg_m2(data, superficie)

            data_completa = data.model_copy(
                update={
                    "esquema": esquema,
                    "dosis_mg_m2": dosis_mg_m2,
                }
            )

            if not data_completa.dosis_por_farmaco and self._dosis_service is not None:
                refs = self._dosis_service.dosis_referencia_regimen(
                    data_completa.id_regimen,
                    superficie,
                    data_completa.peso_kg,
                )
                from backend.models.prescription import DosisFarmaco

                dosis_objs = [DosisFarmaco(**item) for item in refs]
                data_completa = data_completa.model_copy(update={"dosis_por_farmaco": dosis_objs})

            validacion = self._validation_service.validate(data_completa)

            # RF-34: si el motor detecto una alternativa terapeuticamente
            # equivalente de menor costo, la eleccion del esquema mas caro debe
            # venir fundamentada. No se rechaza la prescripcion por su costo
            # ---la decision es clinica--- pero si se exige que quede asentada
            # la razon, que viaja al registro inmutable junto con el resto del
            # expediente y queda disponible para el auditor.
            if validacion.requiere_justificacion_costo:
                justificacion = (data_completa.justificacion_costo or "").strip()
                if len(justificacion) < 5:
                    mejor = validacion.alternativas_economicas[0]
                    raise DomainError(
                        "Existe una alternativa terapeuticamente equivalente de menor costo "
                        "(%s, %s, %.1f%% mas economica). Para prescribir el esquema elegido "
                        "debe consignarse una justificacion clinica en el campo "
                        "'justificacion_costo'." % (mejor.id_regimen, mejor.nombre, mejor.pct_ahorro),
                        status_code=422,
                        error_type="validation_error",
                    )

            clinical = ClinicalData(
                superficie_corporal_m2=superficie,
                prescriptor_username=prescriptor_username,
                **data_completa.model_dump(),
            )
            created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            canonical = build_canonical_payload(
                clinical.model_dump(),
                validacion.model_dump(),
                created_at,
            )

            prescription_id = str(ULID())
            try:
                result = self._repo.create(prescription_id, canonical)
            except FabricBusinessError as exc:
                # Doble submit del mismo ULID (reintento tras timeout): la
                # transaccion anterior llego a commitear, se devuelve el asset.
                if self._repo.is_already_exists(exc):
                    asset = self._repo.get(prescription_id, actor="prescriptor")
                    if asset is not None:
                        return _asset_to_prescription(asset)
                raise

            return _asset_to_prescription(result["asset"], tx_id=result["tx_id"])
        except DomainError:
            # Validaciones de negocio (paciente inexistente, RF-34): esperadas,
            # no ameritan un traceback en el log.
            raise
        except Exception as exc:
            logger.error("Error al crear prescripcion: %s", exc, exc_info=True)
            raise

    def list(
        self,
        page_size: int = 50,
        bookmark: str = "",
        estado: str | None = None,
        actor: str = "prepaga",
    ) -> PrescriptionList:
        """Lista prescripciones desde Fabric (paginacion por bookmark)."""
        try:
            if estado:
                paged = self._repo.list_by_estado(estado, page_size, bookmark, actor=actor)
            else:
                paged = self._repo.list(page_size, bookmark, actor=actor)
            return _paged_to_list(paged)
        except Exception as exc:
            logger.error("Error al listar prescripciones: %s", exc, exc_info=True)
            raise

    def by_patient(
        self,
        patient_id: int,
        page_size: int = 50,
        bookmark: str = "",
        actor: str = "prepaga",
    ) -> PrescriptionList:
        """Prescripciones de un paciente (seudonimo patient_id)."""
        try:
            paged = self._repo.list_by_patient(patient_id, page_size, bookmark, actor=actor)
            return _paged_to_list(paged)
        except Exception as exc:
            logger.error("Error al listar prescripciones del paciente %s: %s", patient_id, exc, exc_info=True)
            raise

    def get(self, prescription_id: str, actor: str = "prepaga") -> Prescription:
        """Detalle de una prescripcion, leido de Fabric."""
        asset = self._repo.get(prescription_id, actor=actor)
        if asset is None:
            raise NotFoundError(f"Prescripcion {prescription_id} no encontrada")
        return _asset_to_prescription(asset)

    def history(self, prescription_id: str, actor: str = "prepaga") -> list[dict]:
        """Historial de transacciones Fabric de la prescripcion (tx_id reales)."""
        history = self._repo.history(prescription_id, actor=actor)
        if not history:
            # Distinguir "sin historial" de "no existe".
            if self._repo.get(prescription_id, actor=actor) is None:
                raise NotFoundError(f"Prescripcion {prescription_id} no encontrada")
        return history

    def verify(self, prescription_id: str, actor: str = "prepaga") -> VerifyResult:
        """Verifica la cadena de hashes del asset (payload_hash + eventos)."""
        asset = self._repo.get(prescription_id, actor=actor)
        if asset is None:
            raise NotFoundError(f"Prescripcion {prescription_id} no encontrada")
        resultado = verify_chain(asset)
        return VerifyResult(
            prescription_id=prescription_id,
            valido=resultado["valido"],
            errores=resultado["errores"],
            payload_hash=asset.get("payload_hash"),
            current_hash=asset.get("current_hash"),
        )
