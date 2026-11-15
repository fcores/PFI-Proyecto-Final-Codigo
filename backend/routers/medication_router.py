from fastapi import APIRouter, File, Form, Header, UploadFile

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_medication_service
from backend.models.bulk_import import BulkImportResult
from backend.models.medication import Medication, MedicationList
from backend.services.excel_import_service import MAX_IMPORT_BYTES

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("", response_model=Medication)
def create_medication(
    descripcion: str = Form(...),
    ean: str = Form(...),
    codigo_alfabeta: str = Form(...),
    tipo_conservacion: str = Form(...),
    laboratorio: str = Form(...),
    monodroga: str = Form(...),
    tamano_dimension: str = Form(...),
    potencia_mg: float | None = Form(default=None),
    unidad_potencia: str | None = Form(default=None),
    precio: float | None = Form(default=None),
    via_administracion: str | None = Form(default=None),
    authorization: str | None = Header(default=None),
):
    """Crea un medicamento nuevo con codigo autogenerado. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador", "super_admin"])
    svc = get_medication_service()
    return svc.create(
        descripcion=descripcion,
        ean=ean,
        codigo_alfabeta=codigo_alfabeta,
        tipo_conservacion=tipo_conservacion,
        laboratorio=laboratorio,
        monodroga=monodroga,
        tamano_dimension=tamano_dimension,
        potencia_mg=potencia_mg,
        unidad_potencia=unidad_potencia,
        precio=precio,
        via_administracion=via_administracion,
    )


@router.get("", response_model=MedicationList)
def list_medications(authorization: str | None = Header(default=None)):
    """Lista todos los medicamentos (lectura para prescribir o administrar)."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador", "super_admin"])
    svc = get_medication_service()
    return svc.list_all()


@router.post("/bulk-import", response_model=BulkImportResult)
def bulk_import_medications(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """Importa medicamentos masivamente desde Excel. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador", "super_admin"])
    svc = get_medication_service()
    file_bytes = file.file.read(MAX_IMPORT_BYTES + 1)
    return svc.bulk_import(file_bytes, file.filename or "medicamentos.xlsx")
