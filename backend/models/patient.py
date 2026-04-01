from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class PatientBase(BaseModel):
    sap_id: str = Field(..., title="ID Paciente SAP")
    credential_id: Optional[str] = Field(None, title="ID Credencial")
    provider_id: Optional[str] = Field(None, title="ID Prestador")
    provider: Optional[str] = Field(None, title="Prestador")
    first_name: str = Field(..., title="Nombre")
    last_name: str = Field(..., title="Apellido")
    birth_date: date = Field(..., title="Fecha de nacimiento")
    gender: str = Field(..., title="Género")
    treatment: Optional[str] = Field(None, title="Tratamiento")
    medications: List[str] = Field(default_factory=list, title="Medicamentos")
    # Campos de empadronamiento
    tipo_empadronamiento: str = Field(..., title="Tipo de empadronamiento")
    fecha_inicio: date = Field(..., title="Fecha de inicio del empadronamiento")
    fecha_primera_toma: date = Field(..., title="Fecha de la primera toma")
    cadencia_estimada_toma: int = Field(..., ge=1, title="Cadencia estimada de toma (días)")


class Patient(PatientBase):
    id: int
    hc_filename: Optional[str] = None
    ap_filename: Optional[str] = None
    img_filename: Optional[str] = None
    lab_filename: Optional[str] = None
    receta_filename: Optional[str] = None
    otros_filename: Optional[str] = None


class PatientList(BaseModel):
    patients: List[Patient]
