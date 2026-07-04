from fastapi import APIRouter

from backend.models.prescription import Prescription, PrescriptionBase, PrescriptionList
from backend.dependencies import get_prescription_service

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.post("", response_model=Prescription)
async def create_prescription(data: PrescriptionBase):
    svc = get_prescription_service()
    return svc.create(data)


@router.get("", response_model=PrescriptionList)
async def list_prescriptions():
    svc = get_prescription_service()
    return svc.list_all()
