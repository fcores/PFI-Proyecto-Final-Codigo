from fastapi import APIRouter, File, Form, Header, UploadFile

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_monodrug_service
from backend.models.bulk_import import BulkImportResult
from backend.models.monodrug import Monodrug, MonodrugList
from backend.services.excel_import_service import MAX_IMPORT_BYTES

router = APIRouter(prefix="/monodrugs", tags=["monodrugs"])


@router.post("", response_model=Monodrug)
def create_monodrug(
    descripcion: str = Form(...),
    authorization: str | None = Header(default=None),
):
    """Crea una monodroga nueva con codigo autogenerado. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador", "super_admin"])
    svc = get_monodrug_service()
    return svc.create(descripcion=descripcion)


@router.get("", response_model=MonodrugList)
def list_monodrugs(authorization: str | None = Header(default=None)):
    """Lista todas las monodrogas (lectura para prescribir o administrar)."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador", "super_admin"])
    svc = get_monodrug_service()
    return svc.list_all()


@router.post("/bulk-import", response_model=BulkImportResult)
def bulk_import_monodrugs(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """Importa monodrogas masivamente desde Excel. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador", "super_admin"])
    svc = get_monodrug_service()
    file_bytes = file.file.read(MAX_IMPORT_BYTES + 1)
    return svc.bulk_import(file_bytes, file.filename or "monodrogas.xlsx")
