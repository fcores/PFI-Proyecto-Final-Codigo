"""
Composition root: instancias singleton de repos y servicios.
Centraliza la inyección para que los routers no conozcan las implementaciones.
Las migraciones se ejecutan via Alembic como paso explicito del despliegue,
no al importar este modulo.
"""

from backend.repositories import (
    AuditRepository,
    LedgerRepository,
    MedicationRepository,
    MonodrugRepository,
    PatientRepository,
    PrescriptionRepository,
)
from backend.services import (
    AuditService,
    AuthService,
    LedgerService,
    MedicationService,
    MonodrugService,
    PatientService,
    PrescriptionService,
    ValidationService,
)
from backend.services.dosis_service import DosisService
from backend.services.excel_import_service import ExcelImportService
from backend.services.recomendacion_service import RecomendacionService

_patient_repo = PatientRepository()
_medication_repo = MedicationRepository()
_monodrug_repo = MonodrugRepository()
_prescription_repo = PrescriptionRepository()
_ledger_repo = LedgerRepository()
_audit_repo = AuditRepository()
_excel_import_service = ExcelImportService()
_dosis_service = DosisService(_medication_repo)

_patient_service = PatientService(_patient_repo, _excel_import_service)
_monodrug_service = MonodrugService(_monodrug_repo, _excel_import_service)
_medication_service = MedicationService(
    _medication_repo,
    _monodrug_repo,
    _excel_import_service,
    _monodrug_service,
)
_validation_service = ValidationService(_dosis_service)
_ledger_service = LedgerService(_ledger_repo)
_prescription_service = PrescriptionService(
    _prescription_repo,
    _validation_service,
    _ledger_service,
    _audit_repo,
    _dosis_service,
)
_auth_service = AuthService()
_audit_service = AuditService(_audit_repo, _ledger_service)
_recomendacion_service = RecomendacionService(_dosis_service)


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


def get_recomendacion_service() -> RecomendacionService:
    """Retorna la instancia singleton de RecomendacionService."""
    return _recomendacion_service


def get_dosis_service() -> DosisService:
    """Retorna la instancia singleton de DosisService."""
    return _dosis_service
