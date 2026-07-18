from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EnrollmentBase(BaseModel):
    medications: List[str] = Field(..., min_length=1, title="Medicamentos")
    diagnostico: str = Field(..., title="Diagnóstico")


class Enrollment(EnrollmentBase):
    id: int
    enrollment_code: str = Field(..., title="ID de empadronamiento")
    tipo: str = Field(..., title="Tipo de empadronamiento")
    created_at: datetime = Field(..., title="Fecha de creación")
    blockchain_tx_id: Optional[str] = Field(None, title="ID de transacción en blockchain")


class EnrollmentList(BaseModel):
    enrollments: List[Enrollment]
