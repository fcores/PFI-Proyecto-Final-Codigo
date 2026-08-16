from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import (
    get_dosis_service,
    get_prescription_service,
    get_recomendacion_service,
)
from backend.ml.regimenes import REGIMENES
from backend.models.prescription import (
    DosisFarmaco,
    Prescription,
    PrescriptionBase,
    PrescriptionList,
    RecomendacionRequest,
    RecomendacionResponse,
)

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


class RegimenInfo(BaseModel):
    """Informacion de catalogo de un regimen."""

    id_regimen: str
    nombre: str
    farmacos: list[str]


class RegimenList(BaseModel):
    """Lista de regimenes disponibles."""

    regimenes: list[RegimenInfo]


@router.get("/regimenes", response_model=RegimenList)
async def listar_regimenes(authorization: str | None = Header(default=None)):
    """Lista los regimenes R00-R13 del nucleo compartido."""
    require_auth(authorization)
    items = []
    for rid, info in REGIMENES.items():
        items.append(
            RegimenInfo(
                id_regimen=rid,
                nombre=info["nombre"],
                farmacos=list(info["farmacos"]),
            )
        )
    return RegimenList(regimenes=items)


@router.get("/dosis-referencia", response_model=list[DosisFarmaco])
async def dosis_referencia(
    id_regimen: str = Query(...),
    peso_kg: float = Query(..., gt=0),
    talla_cm: float = Query(..., gt=0),
    authorization: str | None = Header(default=None),
):
    """Devuelve la dosis de referencia por farmaco para un regimen."""
    require_auth(authorization)
    import math

    bsa = math.sqrt((talla_cm * peso_kg) / 3600.0)
    svc = get_dosis_service()
    refs = svc.dosis_referencia_regimen(id_regimen, bsa, peso_kg)
    return [DosisFarmaco(**item) for item in refs]


@router.post("/recomendacion", response_model=RecomendacionResponse)
async def recomendar_regimen(
    data: RecomendacionRequest,
    authorization: str | None = Header(default=None),
):
    """Sugiere un regimen segun guias clinicas. No usa el modelo ML."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador"])
    svc = get_recomendacion_service()
    return svc.recomendar(data)


@router.post("", response_model=Prescription)
async def create_prescription(
    data: PrescriptionBase,
    authorization: str | None = Header(default=None),
):
    """Crea una prescripcion nueva. Requiere rol prescriptor o administrador."""
    user = require_auth(authorization)
    require_role(user, ["prescriptor", "administrador"])
    svc = get_prescription_service()
    return svc.create(data)


@router.get("", response_model=PrescriptionList)
async def list_prescriptions(
    limit: int = Query(100, ge=1, le=500, description="Cantidad maxima de resultados"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginacion"),
    authorization: str | None = Header(default=None),
):
    """Lista prescripciones con paginacion. Requiere autenticacion."""
    require_auth(authorization)
    svc = get_prescription_service()
    return svc.list_all(limit=limit, offset=offset)
