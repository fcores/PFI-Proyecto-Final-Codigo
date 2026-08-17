"""Router de prescripciones. Los datos viven en Fabric (sin copia en RDS).

Matriz de roles:
- crear / recomendacion / dosis-referencia: prescriptor, super_admin
- listados, detalle, historial, verificacion: prescriptor, auditor, super_admin
El actor con el que se lee de Fabric se deriva del rol (prescriptor/auditor
usan la identidad de su organizacion; el resto lee como la prepaga).
"""

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import (
    get_dosis_service,
    get_prescription_service,
    get_recomendacion_service,
)
from backend.ml.regimenes import REGIMENES
from backend.models.auth import UserInfo
from backend.models.prescription import (
    ESTADOS_PRESCRIPCION,
    DosisFarmaco,
    Prescription,
    PrescriptionBase,
    PrescriptionList,
    RecomendacionRequest,
    RecomendacionResponse,
    VerifyResult,
)

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

_ROLES_LECTURA = ["prescriptor", "auditor", "super_admin"]
_ROLES_ESCRITURA = ["prescriptor", "super_admin"]


def _actor_for(user: UserInfo) -> str:
    """Organizacion Fabric con la que firma/lee segun el rol del usuario."""
    if user.role == "prescriptor":
        return "prescriptor"
    if user.role == "auditor":
        return "auditor"
    return "prepaga"


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
    user = require_auth(authorization)
    require_role(user, _ROLES_LECTURA)
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
    user = require_auth(authorization)
    require_role(user, _ROLES_ESCRITURA)
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
    require_role(user, _ROLES_ESCRITURA)
    svc = get_recomendacion_service()
    return svc.recomendar(data)


@router.post("", response_model=Prescription)
async def create_prescription(
    data: PrescriptionBase,
    authorization: str | None = Header(default=None),
):
    """Crea una prescripcion: la valida con el motor ML y la asienta en Fabric."""
    user = require_auth(authorization)
    require_role(user, _ROLES_ESCRITURA)
    svc = get_prescription_service()
    return svc.create(data)


@router.get("", response_model=PrescriptionList)
async def list_prescriptions(
    estado: str | None = Query(None, description="Filtra por estado del ciclo de auditoria"),
    page_size: int = Query(50, ge=1, le=200, description="Tamano de pagina"),
    bookmark: str = Query("", description="Bookmark devuelto por la pagina anterior"),
    authorization: str | None = Header(default=None),
):
    """Lista prescripciones desde Fabric con paginacion por bookmark."""
    user = require_auth(authorization)
    require_role(user, _ROLES_LECTURA)
    if estado is not None and estado not in ESTADOS_PRESCRIPCION:
        from backend.error_handlers import DomainError

        raise DomainError(
            f"Estado invalido: {estado}. Validos: {', '.join(ESTADOS_PRESCRIPCION)}",
            status_code=422,
            error_type="validation_error",
        )
    svc = get_prescription_service()
    return svc.list(page_size=page_size, bookmark=bookmark, estado=estado, actor=_actor_for(user))


@router.get("/by-patient/{patient_id}", response_model=PrescriptionList)
async def list_by_patient(
    patient_id: int,
    page_size: int = Query(50, ge=1, le=200),
    bookmark: str = Query(""),
    authorization: str | None = Header(default=None),
):
    """Prescripciones de un paciente (seudonimo patient_id)."""
    user = require_auth(authorization)
    require_role(user, _ROLES_LECTURA)
    svc = get_prescription_service()
    return svc.by_patient(patient_id, page_size=page_size, bookmark=bookmark, actor=_actor_for(user))


@router.get("/{prescription_id}", response_model=Prescription)
async def get_prescription(
    prescription_id: str,
    authorization: str | None = Header(default=None),
):
    """Detalle de una prescripcion, leido de Fabric."""
    user = require_auth(authorization)
    require_role(user, _ROLES_LECTURA)
    svc = get_prescription_service()
    return svc.get(prescription_id, actor=_actor_for(user))


@router.get("/{prescription_id}/history")
async def get_prescription_history(
    prescription_id: str,
    authorization: str | None = Header(default=None),
):
    """Historial de transacciones Fabric de la prescripcion (tx_id reales)."""
    user = require_auth(authorization)
    require_role(user, _ROLES_LECTURA)
    svc = get_prescription_service()
    return {"prescription_id": prescription_id, "history": svc.history(prescription_id, actor=_actor_for(user))}


@router.get("/{prescription_id}/verify", response_model=VerifyResult)
async def verify_prescription(
    prescription_id: str,
    authorization: str | None = Header(default=None),
):
    """Verifica la cadena de hashes del asset (payload + eventos de auditoria)."""
    user = require_auth(authorization)
    require_role(user, _ROLES_LECTURA)
    svc = get_prescription_service()
    return svc.verify(prescription_id, actor=_actor_for(user))
