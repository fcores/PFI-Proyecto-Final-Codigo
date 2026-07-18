import logging
import math
from datetime import datetime

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
    ) -> None:
        """Inicializa el servicio de prescripciones."""
        try:
            self._repo = repo
            self._validation_service = validation_service
            self._ledger_service = ledger_service
            self._audit_repo = audit_repo
        except Exception as exc:
            logger.error("Error al inicializar PrescriptionService: %s", exc, exc_info=True)
            raise

    @staticmethod
    def _build_code(seq: int) -> str:
        """Genera el codigo de prescripcion a partir del numero de secuencia."""
        try:
            return f"PRESC-{seq:04d}"
        except Exception as exc:
            logger.error("Error al generar codigo de prescripcion: %s", exc, exc_info=True)
            raise

    @staticmethod
    def _body_surface_area(peso_kg: float, talla_cm: float) -> float:
        """Calcula la superficie corporal con la formula de Mosteller."""
        try:
            return round(math.sqrt((talla_cm * peso_kg) / 3600.0), 2)
        except Exception as exc:
            logger.error("Error al calcular superficie corporal: %s", exc, exc_info=True)
            raise

    def create(self, data: PrescriptionBase) -> Prescription:
        """Crea una prescripcion, la valida, registra en blockchain y genera caso de auditoria si aplica."""
        try:
            seq = self._repo.next_id()
            validacion = self._validation_service.validate(data)
            superficie = self._body_surface_area(data.peso_kg, data.talla_cm)

            payload = {
                "prescription_code": self._build_code(seq),
                "patient_sap_id": data.patient_sap_id,
                "diagnostico_cie10": data.diagnostico_cie10,
                "estadio": data.estadio,
                "esquema": data.esquema,
                "dosis_mg_m2": data.dosis_mg_m2,
                "superficie_corporal_m2": superficie,
                "estado_validacion": validacion.estado,
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
                **data.model_dump(),
            )
            saved = self._repo.add(prescription)

            if validacion.estado == "REVISION":
                self._audit_repo.add_case(saved.id, "pendiente")

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
