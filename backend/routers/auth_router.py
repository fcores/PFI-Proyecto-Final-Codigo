from typing import Optional

from fastapi import APIRouter, Header

from backend.models.auth import LoginRequest, LoginResponse, UserInfo
from backend.dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    svc = get_auth_service()
    return svc.login(data.username, data.password)


@router.get("/me", response_model=UserInfo)
async def me(authorization: Optional[str] = Header(default=None)):
    svc = get_auth_service()
    return svc.resolve(_extract_token(authorization))


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(default=None)):
    svc = get_auth_service()
    svc.logout(_extract_token(authorization))
    return {"message": "Sesión cerrada."}
