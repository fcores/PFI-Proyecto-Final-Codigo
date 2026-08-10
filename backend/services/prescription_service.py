"""Servicio de gestion de prescripciones medicas."""
import json
import logging
import math
from datetime import datetime

from backend.ml.regimenes import nombre_regimen
from backend.models.prescription import Prescription, PrescriptionBase, PrescriptionList
from backend.repositories.audit_repo import AuditRepository
from backend.repositories.prescription_repo import PrescriptionRepository
from backend.services.ledger_service import LedgerService
from backend.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class PrescriptionService:
    """Servicio de gestion de prescripciones medicas."""

    def __init__(
        self,
        repo: PrescriptionRepository,
        validation_service: ValidationService,
        ledger_service: LedgerService,
        audit_repo: AuditRepository,
        dosis_service=None,
    ) -> None:
        """Inicializa el servicio de prescripciones."""
        try:
            self._repo = repo
            self._validation_service = validation_service
            self._ledger_service = ledger_service
            self._audit_repo = audit_repo
            self._dosis_service = dosis_service
        except Exception as exc:
            logger.error("Error al inicializar PrescriptionService: %s", exc, exc_info=True)
            raise

    def _build_code(self, seq: int) -> str:
        """Genera el codigo de prescripcion a partir del numero de secuencia."""
        try:
            return "PRESC-%04d" % seq
        except Exception as exc:
            logger.error("Error al generar codigo de prescripcion: %s", exc, exc_info=True)
            raise

    def _body_surface_area(self, peso_kg: float, talla_cm: float) -> float:
        """Calcula la superficie corporal con la formula de Mosteller."""
        try:
            return round(math.sqrt((talla_cm * peso_kg) / 3600.0), 2)
        except Exception as exc:
            logger.error("Error al calcular superficie corporal: %s", exc, exc_info=True)
            raise

    def _derivar_dosis_mg_m2(self, data: PrescriptionBase, superficie: float) -> float:
        """Deriva un valor representativo de dosis_mg_m2 para compatibilidad."""
        try:
            if data.dosis_mg_m2 is not None and data.dosis_mg_m2 > 0:
                return float(data.dosis_mg_m2)
            if data.dosis_por_farmaco and superficie > 0:
                total = 0.0
                for item in data.dosis_por_farmaco:
                    total += float(item.dosis_mg)
                if total > 0:
                    return round(total / superficie, 2)
            return 0.01
        except Exception as exc:
            logger.error("Error al derivar dosis_mg_m2: %s", exc, exc_info=True)
            raise

    def _asegurar_esquema(self, data: PrescriptionBase) -> str:
        """Completa el esquema legible a partir del regimen si falta."""
        try:
            if data.esquema and str(data.esquema).strip():
                return data.esquema
            return nombre_regimen(data.id_regimen)
        except Exception as exc:
            logger.error("Error al asegurar esquema: %s", exc, exc_info=True)
            raise

    def create(self, data: PrescriptionBase) -> Prescription:
        """Crea una prescripcion, la valida, registra en blockchain y genera caso de auditoria si aplica."""
        try:
            seq = self._repo.next_id()
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

            payload = {
                "prescription_code": self._build_code(seq),
                "patient_sap_id": data_completa.patient_sap_id,
                "diagnostico_cie10": data_completa.diagnostico_cie10,
                "estadio": data_completa.estadio,
                "id_regimen": data_completa.id_regimen,
                "esquema": data_completa.esquema,
                "dosis_mg_m2": data_completa.dosis_mg_m2,
                "superficie_corporal_m2": superficie,
                "estado_validacion": validacion.estado,
                "probabilidad_concordante": validacion.probabilidad_concordante,
                "origen_validacion": validacion.origen,
                "version_modelo": validacion.version_modelo,
            }
            block = self._ledger_service.append("prescription", payload)

            prescription = Prescription(
                id=seq,
                prescription_code=self._build_code(seq),
                superficie_corporal_m2=superficie,
                created_at=datetime.now(),
                validacion=validacion,
                blockchain_tx_id=block.hash,
                block_index=block.index,
                **data_completa.model_dump(),
            )
            saved = self._repo.add(prescription)

            if validacion.estado == "REVISION":
                self._audit_repo.add_case(
                    saved.id,
                    "pendiente",
                    snapshot={
                        "prescription_code": saved.prescription_code,
                        "patient_sap_id": saved.patient_sap_id,
                        "diagnostico_cie10": saved.diagnostico_cie10,
                        "estadio": saved.estadio,
                        "esquema": saved.esquema,
                        "id_regimen": saved.id_regimen,
                        "dosis_mg_m2": saved.dosis_mg_m2,
                        "superficie_corporal_m2": saved.superficie_corporal_m2,
                        "estado_validacion": validacion.estado,
                        "motivos_validacion": json.dumps(validacion.motivos),
                        "probabilidad_concordante": validacion.probabilidad_concordante,
                        "nivel_confianza": validacion.nivel_confianza,
                        "umbral_bajo": validacion.umbral_bajo,
                        "umbral_alto": validacion.umbral_alto,
                        "origen_validacion": validacion.origen,
                        "version_modelo": validacion.version_modelo,
                        "features_relevantes": json.dumps(
                            [f.model_dump() for f in validacion.features_relevantes]
                        ),
                        "prescription_created_at": saved.created_at,
                    },
                )

            return saved
        except Exception as exc:
            logger.error("Error al crear prescripcion: %s", exc, exc_info=True)
            raise

    def list_all(self) -> PrescriptionList:
        """Lista todas las prescripciones."""
        try:
            return PrescriptionList(prescriptions=self._repo.list_all())
        except Exception as exc:
            logger.error("Error al listar prescripciones: %s", exc, exc_info=True)
            raise
