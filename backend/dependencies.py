"""
Composition root: instancias singleton de repos y servicios.
Centraliza la inyección para que los routers no conozcan las implementaciones.
"""
from backend.repositories import (
    PatientRepository,
    AgreementRepository,
    EnrollmentRepository,
    MedicationRepository,
    MonodrugRepository,
)
from backend.services import (
    PatientService,
    AgreementService,
    EnrollmentService,
    MedicationService,
    MonodrugService,
)
from backend.services.excel_import_service import ExcelImportService

_patient_repo = PatientRepository()
_agreement_repo = AgreementRepository()
_enrollment_repo = EnrollmentRepository()
_medication_repo = MedicationRepository()
_monodrug_repo = MonodrugRepository()
_excel_import_service = ExcelImportService()

_patient_service = PatientService(_patient_repo, _excel_import_service)
_agreement_service = AgreementService(_agreement_repo, _excel_import_service)
_enrollment_service = EnrollmentService(_enrollment_repo, _excel_import_service)
_monodrug_service = MonodrugService(_monodrug_repo, _excel_import_service)
_medication_service = MedicationService(_medication_repo, _monodrug_repo, _excel_import_service)


def get_patient_service() -> PatientService:
    return _patient_service


def get_agreement_service() -> AgreementService:
    return _agreement_service


def get_enrollment_service() -> EnrollmentService:
    return _enrollment_service


def get_medication_service() -> MedicationService:
    return _medication_service


def get_monodrug_service() -> MonodrugService:
    return _monodrug_service
