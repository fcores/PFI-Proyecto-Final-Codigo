from fastapi import APIRouter, File, Form, UploadFile

from backend.dependencies import get_medication_service
from backend.models.bulk_import import BulkImportResult
from backend.models.medication import Medication, MedicationList

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("", response_model=Medication)
async def create_medication(
    descripcion: str = Form(...),
    ean: str = Form(...),
    codigo_alfabeta: str = Form(...),
    tipo_conservacion: str = Form(...),
    sap_id: str = Form(...),
    monodroga_id: str = Form(...),
    tamano_dimension: str = Form(...),
):
    svc = get_medication_service()
    return svc.create(
        descripcion=descripcion,
        ean=ean,
        codigo_alfabeta=codigo_alfabeta,
        tipo_conservacion=tipo_conservacion,
        sap_id=sap_id,
        monodroga_id=monodroga_id,
        tamano_dimension=tamano_dimension,
    )


@router.get("", response_model=MedicationList)
async def list_medications():
    svc = get_medication_service()
    return svc.list_all()


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_medications(file: UploadFile = File(...)):
    svc = get_medication_service()
    file_bytes = await file.read()
    return svc.bulk_import(file_bytes, file.filename or "medicamentos.xlsx")
