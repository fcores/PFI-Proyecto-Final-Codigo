from fastapi import APIRouter

from backend.models.ledger import LedgerList, LedgerVerification
from backend.dependencies import get_ledger_service

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("", response_model=LedgerList)
async def list_ledger():
    svc = get_ledger_service()
    return svc.list_blocks()


@router.get("/verify", response_model=LedgerVerification)
async def verify_ledger():
    svc = get_ledger_service()
    return svc.verify_chain()
