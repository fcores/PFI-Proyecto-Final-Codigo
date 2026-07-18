from typing import Optional

from fastapi import APIRouter, Header

from backend.auth_middleware import require_auth, require_role
from backend.models.prescription import Prescription, PrescriptionBase, PrescriptionList
from backend.dependencies import get_prescription_service

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.post("", response_model=Prescription)
async def create_prescription(
    data: PrescriptionBase,
    authorization: Optional[str] = Header(default=None),
):
    """Crea una prescripcion nueva. Requiere rol prescriptor o administrador."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador"])
    svc = get_prescription_service()
    return svc.create(data)


@router.get("", response_model=PrescriptionList)
async def list_prescriptions(authorization: Optional[str] = Header(default=None)):
    """Lista todas las prescripciones. Requiere autenticacion."""
    require_auth(authorization)
    svc = get_prescription_service()
    return svc.list_all()
