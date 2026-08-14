from fastapi import APIRouter, Header

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_ledger_service
from backend.models.ledger import LedgerList, LedgerVerification

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("", response_model=LedgerList)
async def list_ledger(authorization: str | None = Header(default=None)):
    """Lista los bloques del ledger. Requiere autenticacion."""
    require_auth(authorization)
    svc = get_ledger_service()
    return svc.list_blocks()


@router.get("/verify", response_model=LedgerVerification)
async def verify_ledger(authorization: str | None = Header(default=None)):
    """Verifica la integridad de la cadena del ledger. Requiere rol auditor o administrador."""
    user = require_auth(authorization)
    require_role(user, ["auditor", "administrador"])
    svc = get_ledger_service()
    return svc.verify_chain()
