from datetime import date

from pydantic import BaseModel, Field


class PatientBase(BaseModel):
    credential_id: str | None = Field(None, title="ID Credencial")
    provider_id: str | None = Field(None, title="ID Prestador")
    provider: str | None = Field(None, title="Prestador")
    first_name: str = Field(..., title="Nombre")
    last_name: str = Field(..., title="Apellido")
    birth_date: date = Field(..., title="Fecha de nacimiento")
    gender: str = Field(..., title="Género")
    treatment: str | None = Field(None, title="Tratamiento")
    medications: list[str] = Field(default_factory=list, title="Medicamentos")


class Patient(PatientBase):
    id: int
    hc_filename: str | None = None
    ap_filename: str | None = None
    img_filename: str | None = None
    lab_filename: str | None = None
    receta_filename: str | None = None
    otros_filename: str | None = None


class PatientList(BaseModel):
    patients: list[Patient]
