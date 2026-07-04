from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., title="Usuario")
    password: str = Field(..., title="Contraseña")


class UserInfo(BaseModel):
    username: str = Field(..., title="Usuario")
    display_name: str = Field(..., title="Nombre a mostrar")


class LoginResponse(BaseModel):
    token: str = Field(..., title="Token de sesión")
    user: UserInfo = Field(..., title="Usuario autenticado")
