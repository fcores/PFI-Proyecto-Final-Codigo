from .patient_router import router as patient_router
from .agreement_router import router as agreement_router
from .enrollment_router import router as enrollment_router
from .medication_router import router as medication_router
from .monodrug_router import router as monodrug_router

__all__ = [
    "patient_router",
    "agreement_router",
    "enrollment_router",
    "medication_router",
    "monodrug_router",
]
