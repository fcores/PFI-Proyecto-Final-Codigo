"""
Composition root: instancias singleton de repos y servicios.
Centraliza la inyección para que los routers no conozcan las implementaciones.
Las migraciones se ejecutan via Alembic como paso explicito del despliegue,
no al importar este modulo.

Las prescripciones viven en Fabric: PrescriptionService y AuditService operan
sobre FabricPrescriptionRepository (cliente HTTP al puente fabric-gateway-svc).
"""

from backend.blockchain.fabric_client import FabricClient
from backend.repositories import (
    FabricPrescriptionRepository,
    MedicationRepository,
    MonodrugRepository,
    PatientRepository,
    UserRepository,
)
from backend.services import (
    AuditService,
    AuthService,
    MedicationService,
    MonodrugService,
    PatientService,
    PrescriptionService,
    UserService,
    ValidationService,
)
from backend.services.dosis_service import DosisService
from backend.services.excel_import_service import ExcelImportService
from backend.services.recomendacion_service import RecomendacionService

_patient_repo = PatientRepository()
_medication_repo = MedicationRepository()
_monodrug_repo = MonodrugRepository()
_user_repo = UserRepository()
_fabric_client = FabricClient()
_fabric_prescription_repo = FabricPrescriptionRepository(_fabric_client)
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
_prescription_service = PrescriptionService(
    _fabric_prescription_repo,
    _validation_service,
    _dosis_service,
)
_auth_service = AuthService()
_audit_service = AuditService(_fabric_prescription_repo)
_user_service = UserService(_user_repo)
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


def get_auth_service() -> AuthService:
    """Retorna la instancia singleton de AuthService."""
    return _auth_service


def get_audit_service() -> AuditService:
    """Retorna la instancia singleton del servicio de auditoria."""
    return _audit_service


def get_user_service() -> UserService:
    """Retorna la instancia singleton del servicio de usuarios."""
    return _user_service


def get_recomendacion_service() -> RecomendacionService:
    """Retorna la instancia singleton de RecomendacionService."""
    return _recomendacion_service


def get_dosis_service() -> DosisService:
    """Retorna la instancia singleton de DosisService."""
    return _dosis_service


def get_fabric_client() -> FabricClient:
    """Retorna la instancia singleton del cliente del puente Fabric."""
    return _fabric_client
