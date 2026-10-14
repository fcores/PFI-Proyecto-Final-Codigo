from fastapi import APIRouter, Header

from backend.auth_middleware import extract_token
from backend.dependencies import get_auth_service
from backend.models.auth import ChangePasswordRequest, LoginRequest, LoginResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


# Los handlers son sincronos a proposito: hacen I/O bloqueante (Argon2,
# psycopg2) y FastAPI los ejecuta en el threadpool sin frenar el event loop.


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    """Autentica al usuario y devuelve un token de sesion."""
    svc = get_auth_service()
    return svc.login(data.username, data.password)


@router.get("/me", response_model=UserInfo)
def me(authorization: str | None = Header(default=None)):
    """Devuelve la informacion del usuario autenticado."""
    svc = get_auth_service()
    return svc.resolve(extract_token(authorization))


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    """Cierra la sesion del usuario invalidando el token."""
    svc = get_auth_service()
    svc.logout(extract_token(authorization))
    return {"message": "Sesion cerrada."}


@router.post("/password")
def change_password(data: ChangePasswordRequest, authorization: str | None = Header(default=None)):
    """Cambia la clave del usuario autenticado y cierra sus demas sesiones."""
    svc = get_auth_service()
    svc.change_own_password(extract_token(authorization), data.current_password, data.new_password)
    return {"message": "Contrasena actualizada."}
