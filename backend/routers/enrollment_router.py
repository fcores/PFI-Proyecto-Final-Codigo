from typing import List

from fastapi import APIRouter, File, Form, UploadFile

from backend.models.bulk_import import BulkImportResult
from backend.models.enrollment import Enrollment, EnrollmentList
from backend.dependencies import get_enrollment_service

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("/{tipo}", response_model=Enrollment)
async def create_enrollment(
    tipo: str,
    medications: List[str] = Form(...),
    diagnostico: str = Form(...),
):
    svc = get_enrollment_service()
    return svc.create(
        tipo=tipo,
        medications=medications,
        diagnostico=diagnostico,
    )


@router.get("/{tipo}", response_model=EnrollmentList)
async def list_enrollments(tipo: str):
    svc = get_enrollment_service()
    return svc.list_by_type(tipo)


@router.post("/{tipo}/bulk-import", response_model=BulkImportResult)
async def bulk_import_enrollments(tipo: str, file: UploadFile = File(...)):
    svc = get_enrollment_service()
    file_bytes = await file.read()
    return svc.bulk_import(tipo, file_bytes, file.filename or f"{tipo}.xlsx")
