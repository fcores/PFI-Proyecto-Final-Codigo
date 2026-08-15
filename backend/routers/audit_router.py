"""Router de endpoints de auditoria."""

from fastapi import APIRouter, Header, HTTPException

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_audit_service
from backend.models.audit import (
    CAMPOS_CORREGIBLES,
    AuditCaseDetail,
    AuditCaseList,
    Correction,
    CorrectionList,
    CorrectionRequest,
    Dictamen,
    DictamenRequest,
)

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/queue", response_model=AuditCaseList)
async def list_audit_queue(authorization: str | None = Header(default=None)):
    """Lista los casos pendientes de auditoria."""
    try:
        user = require_auth(authorization)
        require_role(user, ["auditor", "administrador"])
        svc = get_audit_service()
        return svc.list_pending()
    except Exception:
        raise


@router.get("/cases/{case_id}", response_model=AuditCaseDetail)
async def get_audit_case(case_id: int, authorization: str | None = Header(default=None)):
    """Obtiene el detalle completo de un caso de auditoria."""
    try:
        user = require_auth(authorization)
        require_role(user, ["auditor", "administrador"])
        svc = get_audit_service()
        return svc.get_case_detail(case_id)
    except Exception:
        raise


@router.post("/cases/{case_id}/dictamen", response_model=Dictamen)
async def create_dictamen(case_id: int, data: DictamenRequest, authorization: str | None = Header(default=None)):
    """Emite un dictamen sobre un caso de auditoria."""
    try:
        user = require_auth(authorization)
        require_role(user, ["auditor", "administrador"])
        svc = get_audit_service()
        return svc.create_dictamen(case_id, data.resultado, data.justificacion, user.username)
    except Exception:
        raise


@router.post("/cases/{case_id}/corrections", response_model=Correction)
async def create_correction(case_id: int, data: CorrectionRequest, authorization: str | None = Header(default=None)):
    """Registra una correccion de dato clinico."""
    try:
        user = require_auth(authorization)
        require_role(user, ["auditor", "administrador"])
        svc = get_audit_service()
        if data.campo not in CAMPOS_CORREGIBLES:
            raise HTTPException(
                status_code=422,
                detail="Campo no corregible: %s. Validos: %s" % (data.campo, ", ".join(CAMPOS_CORREGIBLES)),
            )
        detail = svc.get_case_detail(case_id)
        # El valor anterior se lee del caso para que la correccion quede
        # trazable; antes se guardaba siempre vacio.
        actual = getattr(detail.case, data.campo, None)
        valor_anterior = "" if actual is None else str(actual)
        return svc.create_correction(
            case_id,
            data.campo,
            valor_anterior,
            data.valor_nuevo,
            data.justificacion,
            user.username,
        )
    except Exception:
        raise


@router.get("/cases/{case_id}/history", response_model=CorrectionList)
async def list_corrections(case_id: int, authorization: str | None = Header(default=None)):
    """Lista el historial de correcciones de un caso."""
    try:
        user = require_auth(authorization)
        require_role(user, ["auditor", "administrador"])
        svc = get_audit_service()
        return svc.list_corrections(case_id)
    except Exception:
        raise
