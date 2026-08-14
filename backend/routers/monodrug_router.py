from fastapi import APIRouter, File, Form, Header, UploadFile

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_monodrug_service
from backend.models.bulk_import import BulkImportResult
from backend.models.monodrug import Monodrug, MonodrugList

router = APIRouter(prefix="/monodrugs", tags=["monodrugs"])


@router.post("", response_model=Monodrug)
async def create_monodrug(
    descripcion: str = Form(...),
    authorization: str | None = Header(default=None),
):
    """Crea una monodroga nueva con codigo autogenerado. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador"])
    svc = get_monodrug_service()
    return svc.create(descripcion=descripcion)


@router.get("", response_model=MonodrugList)
async def list_monodrugs(authorization: str | None = Header(default=None)):
    """Lista todas las monodrogas. Requiere autenticacion."""
    require_auth(authorization)
    svc = get_monodrug_service()
    return svc.list_all()


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_monodrugs(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """Importa monodrogas masivamente desde Excel. Requiere rol administrador."""
    user = require_auth(authorization)
    require_role(user, ["administrador"])
    svc = get_monodrug_service()
    file_bytes = await file.read()
    return svc.bulk_import(file_bytes, file.filename or "monodrogas.xlsx")
