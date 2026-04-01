from datetime import date
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form

from backend.models.bulk_import import BulkImportResult
from backend.models.agreement import Agreement, AgreementList
from backend.dependencies import get_agreement_service

router = APIRouter(prefix="/agreements", tags=["agreements"])


@router.post("", response_model=Agreement)
async def create_agreement(
    laboratorio: str = Form(...),
    prestador: str = Form(...),
    medicamento: str = Form(...),
    medicamento_sap: str = Form(...),
    medico_auditor: Optional[str] = Form(None),
    fecha_inicial: date = Form(...),
    fecha_final: date = Form(...),
    condicion_recupero: str = Form(...),
    contrato_file: Optional[UploadFile] = File(None),
):
    svc = get_agreement_service()
    return svc.create(
        laboratorio=laboratorio,
        prestador=prestador,
        medicamento=medicamento,
        medicamento_sap=medicamento_sap,
        medico_auditor=medico_auditor,
        fecha_inicial=fecha_inicial,
        fecha_final=fecha_final,
        condicion_recupero=condicion_recupero,
        contrato_file=contrato_file,
    )


@router.get("", response_model=AgreementList)
async def list_agreements():
    svc = get_agreement_service()
    return svc.list_all()


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_agreements(file: UploadFile = File(...)):
    svc = get_agreement_service()
    file_bytes = await file.read()
    return svc.bulk_import(file_bytes, file.filename or "acuerdos.xlsx")
