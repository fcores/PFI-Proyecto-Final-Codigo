import logging
from datetime import date

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_patient_service, get_suppression_service
from backend.models.bulk_import import BulkImportResult
from backend.models.patient import Patient, PatientList
from backend.models.suppression import SuppressionCreate, SuppressionList, SuppressionRecord
from backend.services.excel_import_service import MAX_IMPORT_BYTES

logger = logging.getLogger(__name__)

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
    # El frontend envia solo el nombre del archivo: la plataforma registra la
    # constancia de la documentacion pero no almacena el documento.
    hc_filename: str | None = Form(None, max_length=255),
    ap_filename: str | None = Form(None, max_length=255),
    img_filename: str | None = Form(None, max_length=255),
    lab_filename: str | None = Form(None, max_length=255),
    receta_filename: str | None = Form(None, max_length=255),
    otros_filename: str | None = Form(None, max_length=255),
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
        filenames={
            "hc": hc_filename,
            "ap": ap_filename,
            "img": img_filename,
            "lab": lab_filename,
            "receta": receta_filename,
            "otros": otros_filename,
        },
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


def solicitar_supresion(
    patient_id: int,
    data: SuppressionCreate,
    authorization: str | None = Header(default=None),
) -> SuppressionRecord:
    """Registra la solicitud de supresion de un paciente (RF-38). Solo administrador general."""
    try:
        user = require_auth(authorization)
        require_role(user, ["super_admin"])
        return get_suppression_service().solicitar(patient_id, user.username, data.motivo)
    except Exception as exc:
        logger.warning("Solicitud de supresion del paciente %s no completada: %s", patient_id, exc)
        raise


def listar_supresiones(authorization: str | None = Header(default=None)) -> SuppressionList:
    """Lista las solicitudes de supresion. Solo administrador general."""
    try:
        user = require_auth(authorization)
        require_role(user, ["super_admin"])
        return get_suppression_service().listar()
    except Exception as exc:
        logger.warning("Listado de supresiones no completado: %s", exc)
        raise


def ejecutar_supresiones_vencidas(authorization: str | None = Header(default=None)) -> SuppressionList:
    """Ejecuta las solicitudes cuyo periodo de retencion vencio (RF-39). Solo administrador general."""
    try:
        user = require_auth(authorization)
        require_role(user, ["super_admin"])
        return get_suppression_service().ejecutar_vencidas(user.username)
    except Exception as exc:
        logger.warning("Ejecucion de supresiones vencidas no completada: %s", exc)
        raise


router.add_api_route(
    "/{patient_id}/supresion",
    solicitar_supresion,
    methods=["POST"],
    response_model=SuppressionRecord,
)
router.add_api_route(
    "/supresiones/solicitudes",
    listar_supresiones,
    methods=["GET"],
    response_model=SuppressionList,
)
router.add_api_route(
    "/supresiones/ejecutar-vencidas",
    ejecutar_supresiones_vencidas,
    methods=["POST"],
    response_model=SuppressionList,
)
