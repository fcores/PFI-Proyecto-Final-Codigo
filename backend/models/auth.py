"""Modelos de autenticacion, sesion y gestion de usuarios."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Roles del sistema. Debe mantenerse en espejo con el CHECK chk_users_role de
# sql/schema.sql y con la matriz de navegacion del frontend (Sidebar.jsx).
ROLES = ("administrador", "prescriptor", "auditor", "super_admin")

RoleLiteral = Literal["administrador", "prescriptor", "auditor", "super_admin"]


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    display_name: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


class UserAccount(BaseModel):
    """Cuenta de usuario tal como la administra el super admin."""

    id: int
    username: str
    display_name: str
    role: str
    active: bool
    created_at: datetime


class UserList(BaseModel):
    users: list[UserAccount]


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=200)
    role: RoleLiteral


class UserUpdateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=200)
    role: RoleLiteral
    active: bool = True


class PasswordResetRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)
