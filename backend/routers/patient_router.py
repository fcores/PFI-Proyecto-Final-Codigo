from datetime import date

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_patient_service
from backend.models.bulk_import import BulkImportResult
from backend.models.patient import Patient, PatientList
from backend.services.excel_import_service import MAX_IMPORT_BYTES

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=Patient)
def create_patient(
    credential_id: str | None = Form(None),
    provider_id: str | None = Form(None),
    provider: str | None = Form(None),
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: date = Form(...),
    gender: str = Form(...),
    treatment: str | None = Form(None),
    medications: list[str] = Form(default=[]),
    hc_file: UploadFile | None = File(None),
    ap_file: UploadFile | None = File(None),
    img_file: UploadFile | None = File(None),
    lab_file: UploadFile | None = File(None),
    receta_file: UploadFile | None = File(None),
    otros_file: UploadFile | None = File(None),
    authorization: str | None = Header(default=None),
):
    """Crea un paciente nuevo. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador", "super_admin"])
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
def list_patients(
    q: str | None = Query(None, min_length=2, description="Buscar por nombre/apellido"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad maxima de resultados"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginacion"),
    authorization: str | None = Header(default=None),
):
    """Lista pacientes con paginacion. Con ?q= busca por nombre/apellido."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador", "super_admin"])
    svc = get_patient_service()
    if q:
        patients = svc.search(q, username=user.username)
        return PatientList(patients=patients)
    return svc.list_all(limit=limit, offset=offset, username=user.username)


@router.get("/{patient_id}", response_model=Patient)
def get_patient(
    patient_id: int,
    authorization: str | None = Header(default=None),
):
    """Obtiene un paciente por ID."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador", "super_admin"])
    svc = get_patient_service()
    patient = svc.find_by_id(patient_id, username=user.username)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@router.post("/bulk-import", response_model=BulkImportResult)
def bulk_import_patients(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """Importa pacientes masivamente desde Excel. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador", "super_admin"])
    svc = get_patient_service()
    file_bytes = file.file.read(MAX_IMPORT_BYTES + 1)
    return svc.bulk_import(file_bytes, file.filename or "pacientes.xlsx")
