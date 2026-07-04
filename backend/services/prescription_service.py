import math
from datetime import datetime

from backend.models.prescription import Prescription, PrescriptionBase, PrescriptionList
from backend.repositories.prescription_repo import PrescriptionRepository
from backend.services.ledger_service import LedgerService
from backend.services.validation_service import ValidationService


class PrescriptionService:
    def __init__(
        self,
        repo: PrescriptionRepository,
        validation_service: ValidationService,
        ledger_service: LedgerService,
    ) -> None:
        self._repo = repo
        self._validation_service = validation_service
        self._ledger_service = ledger_service

    @staticmethod
    def _build_code(seq: int) -> str:
        return f"PRESC-{seq:04d}"

    @staticmethod
    def _body_surface_area(peso_kg: float, talla_cm: float) -> float:
        # Fórmula de Mosteller: sqrt(talla_cm * peso_kg / 3600)
        return round(math.sqrt((talla_cm * peso_kg) / 3600.0), 2)

    def create(self, data: PrescriptionBase) -> Prescription:
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
        return self._repo.add(prescription)

    def list_all(self) -> PrescriptionList:
        return PrescriptionList(prescriptions=self._repo.list_all())
