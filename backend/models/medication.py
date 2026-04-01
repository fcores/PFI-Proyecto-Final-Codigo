from typing import List, Optional

from pydantic import BaseModel, Field


class MedicationBase(BaseModel):
    descripcion: str = Field(..., title="Descripción")
    ean: str = Field(..., title="EAN")
    codigo_alfabeta: str = Field(..., title="Código Alfabeta")
    tipo_conservacion: str = Field(..., title="Tipo de conservación")
    sap_id: str = Field(..., title="ID SAP")
    monodroga_id: str = Field(..., title="ID de monodroga")
    tamano_dimension: str = Field(..., title="Tamaño / dimensión")


class Medication(MedicationBase):
    id: int
    monodroga_descripcion: Optional[str] = None


class MedicationList(BaseModel):
    medications: List[Medication]
