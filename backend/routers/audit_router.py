"""Router de auditoria on-chain.

La cola y las acciones operan sobre los assets de Fabric. Solo el auditor (y
el super admin) acceden; la accion se firma con la identidad de MedChainMSP.
"""

from fastapi import APIRouter, Header, Query

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_audit_service
from backend.models.audit import AuditActionRequest, AuditDetail
from backend.models.prescription import Prescription, PrescriptionList

router = APIRouter(prefix="/audit", tags=["audit"])

_ROLES_AUDITORIA = ["auditor", "super_admin"]


@router.get("/queue", response_model=PrescriptionList)
def audit_queue(
    estado: str = Query("PENDIENTE_AUDITORIA", description="PENDIENTE_AUDITORIA o EN_REVISION"),
    authorization: str | None = Header(default=None),
):
    """Cola de auditoria completa: pendientes o en revision, mas recientes primero."""
    user = require_auth(authorization)
    require_role(user, _ROLES_AUDITORIA)
    svc = get_audit_service()
    return svc.queue(estado=estado)


@router.get("/{prescription_id}", response_model=AuditDetail)
def audit_detail(
    prescription_id: str,
    authorization: str | None = Header(default=None),
):
    """Detalle para el auditor: asset completo + historial de transacciones."""
    user = require_auth(authorization)
    require_role(user, _ROLES_AUDITORIA)
    svc = get_audit_service()
    return svc.detail(prescription_id)


@router.post("/{prescription_id}/accion", response_model=Prescription)
def audit_action(
    prescription_id: str,
    data: AuditActionRequest,
    authorization: str | None = Header(default=None),
):
    """Registra una accion de auditoria (revision | aprobar | rechazar) on-chain."""
    user = require_auth(authorization)
    require_role(user, _ROLES_AUDITORIA)
    svc = get_audit_service()
    return svc.accion(prescription_id, data.accion, data.justificacion, user.username)
