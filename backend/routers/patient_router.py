from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Header, UploadFile, File, Form, HTTPException, Query

from backend.auth_middleware import require_auth, require_role
from backend.models.bulk_import import BulkImportResult
from backend.models.patient import Patient, PatientList
from backend.dependencies import get_patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=Patient)
async def create_patient(
    credential_id: Optional[str] = Form(None),
    provider_id: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: date = Form(...),
    gender: str = Form(...),
    treatment: Optional[str] = Form(None),
    medications: List[str] = Form(default=[]),
    hc_file: Optional[UploadFile] = File(None),
    ap_file: Optional[UploadFile] = File(None),
    img_file: Optional[UploadFile] = File(None),
    lab_file: Optional[UploadFile] = File(None),
    receta_file: Optional[UploadFile] = File(None),
    otros_file: Optional[UploadFile] = File(None),
    authorization: Optional[str] = Header(default=None),
):
    """Crea un paciente nuevo. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador"])
    svc = get_patient_service()
    return svc.create(
        credential_id=credential_id,
        provider_id=provider_id,
        provider=provider,
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        gender=gender,
        treatment=treatment,
        medications=medications,
        hc_file=hc_file,
        ap_file=ap_file,
        img_file=img_file,
        lab_file=lab_file,
        receta_file=receta_file,
        otros_file=otros_file,
    )


@router.get("", response_model=PatientList)
async def list_patients(
    q: Optional[str] = Query(None, min_length=2, description="Buscar por nombre/apellido"),
    authorization: Optional[str] = Header(default=None),
):
    """Lista pacientes. Con ?q= busca por nombre/apellido."""
    require_auth(authorization)
    svc = get_patient_service()
    if q:
        patients = svc.search(q)
        return PatientList(patients=patients)
    return svc.list_all()


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(
    patient_id: int,
    authorization: Optional[str] = Header(default=None),
):
    """Obtiene un paciente por ID."""
    require_auth(authorization)
    svc = get_patient_service()
    patient = svc.find_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_patients(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    """Importa pacientes masivamente desde Excel. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador"])
    svc = get_patient_service()
    file_bytes = await file.read()
    return svc.bulk_import(file_bytes, file.filename or "pacientes.xlsx")
