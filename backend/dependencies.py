"""
Composition root: instancias singleton de repos y servicios.
Centraliza la inyección para que los routers no conozcan las implementaciones.
"""
from backend.db import init_db

init_db()

from backend.repositories import (
    PatientRepository,
    MedicationRepository,
    MonodrugRepository,
    PrescriptionRepository,
    LedgerRepository,
    AgreementRepository,
    EnrollmentRepository,
    AuditRepository,
)
from backend.services import (
    PatientService,
    MedicationService,
    MonodrugService,
    PrescriptionService,
    ValidationService,
    LedgerService,
    AuthService,
    AgreementService,
    EnrollmentService,
    AuditService,
)
from backend.services.excel_import_service import ExcelImportService

_patient_repo = PatientRepository()
_medication_repo = MedicationRepository()
_monodrug_repo = MonodrugRepository()
_prescription_repo = PrescriptionRepository()
_ledger_repo = LedgerRepository()
_agreement_repo = AgreementRepository()
_enrollment_repo = EnrollmentRepository()
_audit_repo = AuditRepository()
_excel_import_service = ExcelImportService()

_patient_service = PatientService(_patient_repo, _excel_import_service)
_monodrug_service = MonodrugService(_monodrug_repo, _excel_import_service)
_medication_service = MedicationService(_medication_repo, _monodrug_repo, _excel_import_service)
_validation_service = ValidationService()
_ledger_service = LedgerService(_ledger_repo)
_prescription_service = PrescriptionService(_prescription_repo, _validation_service, _ledger_service, _audit_repo)
_auth_service = AuthService()
_agreement_service = AgreementService(_agreement_repo, _excel_import_service)
_enrollment_service = EnrollmentService(_enrollment_repo, _excel_import_service)
_audit_service = AuditService(_audit_repo, _ledger_service)


def get_patient_service() -> PatientService:
    """Retorna la instancia singleton de PatientService."""
    return _patient_service


def get_medication_service() -> MedicationService:
    """Retorna la instancia singleton de MedicationService."""
    return _medication_service


def get_monodrug_service() -> MonodrugService:
    """Retorna la instancia singleton de MonodrugService."""
    return _monodrug_service


def get_prescription_service() -> PrescriptionService:
    """Retorna la instancia singleton de PrescriptionService."""
    return _prescription_service


def get_ledger_service() -> LedgerService:
    """Retorna la instancia singleton de LedgerService."""
    return _ledger_service


def get_auth_service() -> AuthService:
    """Retorna la instancia singleton de AuthService."""
    return _auth_service


def get_audit_service() -> AuditService:
    """Retorna la instancia singleton del servicio de auditoria."""
    return _audit_service


def get_agreement_service() -> AgreementService:
    """Retorna la instancia singleton de AgreementService."""
    return _agreement_service


def get_enrollment_service() -> EnrollmentService:
    """Retorna la instancia singleton de EnrollmentService."""
    return _enrollment_service
