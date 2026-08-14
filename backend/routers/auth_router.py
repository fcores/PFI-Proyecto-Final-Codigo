from fastapi import APIRouter, Header

from backend.auth_middleware import extract_token
from backend.dependencies import get_auth_service
from backend.models.auth import LoginRequest, LoginResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    """Autentica al usuario y devuelve un token de sesion."""
    svc = get_auth_service()
    return svc.login(data.username, data.password)


@router.get("/me", response_model=UserInfo)
async def me(authorization: str | None = Header(default=None)):
    """Devuelve la informacion del usuario autenticado."""
    svc = get_auth_service()
    return svc.resolve(extract_token(authorization))


@router.post("/logout")
async def logout(authorization: str | None = Header(default=None)):
    """Cierra la sesion del usuario invalidando el token."""
    svc = get_auth_service()
    svc.logout(extract_token(authorization))
    return {"message": "Sesion cerrada."}
