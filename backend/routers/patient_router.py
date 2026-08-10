from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Header, UploadFile, File, Form

from backend.auth_middleware import require_auth, require_role
from backend.models.bulk_import import BulkImportResult
from backend.models.patient import Patient, PatientList
from backend.dependencies import get_patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=Patient)
async def create_patient(
    sap_id: str = Form(...),
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
        sap_id=sap_id,
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
async def list_patients(authorization: Optional[str] = Header(default=None)):
    """Lista todos los pacientes. Requiere autenticacion."""
    require_auth(authorization)
    svc = get_patient_service()
    return svc.list_all()


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
