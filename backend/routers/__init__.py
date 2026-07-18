from .patient_router import router as patient_router
from .medication_router import router as medication_router
from .monodrug_router import router as monodrug_router
from .prescription_router import router as prescription_router
from .ledger_router import router as ledger_router
from .auth_router import router as auth_router

__all__ = [
    "patient_router",
    "medication_router",
    "monodrug_router",
    "prescription_router",
    "ledger_router",
    "auth_router",
]
