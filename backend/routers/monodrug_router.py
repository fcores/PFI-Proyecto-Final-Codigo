from fastapi import APIRouter, File, Form, UploadFile

from backend.dependencies import get_monodrug_service
from backend.models.bulk_import import BulkImportResult
from backend.models.monodrug import Monodrug, MonodrugList

router = APIRouter(prefix="/monodrugs", tags=["monodrugs"])


@router.post("", response_model=Monodrug)
async def create_monodrug(
    descripcion: str = Form(...),
    sap_id: str = Form(...),
):
    svc = get_monodrug_service()
    return svc.create(
        descripcion=descripcion,
        sap_id=sap_id,
    )


@router.get("", response_model=MonodrugList)
async def list_monodrugs():
    svc = get_monodrug_service()
    return svc.list_all()


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_monodrugs(file: UploadFile = File(...)):
    svc = get_monodrug_service()
    file_bytes = await file.read()
    return svc.bulk_import(file_bytes, file.filename or "monodrogas.xlsx")
