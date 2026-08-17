from .audit_router import router as audit_router
from .auth_router import router as auth_router
from .health_router import router as health_router
from .medication_router import router as medication_router
from .monodrug_router import router as monodrug_router
from .patient_router import router as patient_router
from .prescription_router import router as prescription_router
from .user_router import router as user_router

__all__ = [
    "patient_router",
    "medication_router",
    "monodrug_router",
    "prescription_router",
    "auth_router",
    "audit_router",
    "user_router",
    "health_router",
]
