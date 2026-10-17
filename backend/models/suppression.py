"""Modelos de supresion de datos de pacientes (RF-38, RF-39)."""

from datetime import datetime

from pydantic import BaseModel, Field


class SuppressionCreate(BaseModel):
    """Solicitud de supresion registrada por el administrador general."""

    motivo: str | None = Field(None, max_length=500, title="Motivo de la solicitud")


class SuppressionRecord(BaseModel):
    """Estado de una solicitud de supresion."""

    id: int
    patient_id: int
    requested_by: str
    motivo: str | None = None
    requested_at: datetime
    ejecutable_desde: datetime
    executed_at: datetime | None = None
    estado: str


class SuppressionList(BaseModel):
    """Listado de solicitudes de supresion."""

    solicitudes: list[SuppressionRecord]


class SelfDeletionRequest(BaseModel):
    """Baja voluntaria de la propia cuenta (RF-37)."""

    password: str = Field(..., min_length=1, max_length=128, title="Contraseña actual")
