from typing import List, Optional

from pydantic import BaseModel, Field


class MedicationBase(BaseModel):
    descripcion: str = Field(..., title="Texto Largo de Material")
    ean: str = Field(..., title="Código EAN/UPC")
    codigo_alfabeta: str = Field(..., title="Nro Troquel Alfabeta")
    tipo_conservacion: str = Field(..., title="Cadena de frío (frio/seco)")
    laboratorio: str = Field(..., title="Laboratorio")
    monodroga: str = Field(..., title="Código de monodroga (nombre de la droga)")
    tamano_dimension: str = Field(..., title="Tamaño / Dimensión")
    potencia_mg: Optional[float] = Field(None, title="Valor de Potencia (mg)")
    unidad_potencia: Optional[str] = Field(None, title="Códigos de Potencia (ej. MG)")
    precio: Optional[float] = Field(None, title="Precio de Venta al Público")
    via_administracion: Optional[str] = Field(None, title="Código de vías de administración")


class Medication(MedicationBase):
    id: int
    codigo: str = Field(..., title="Código autogenerado")


class MedicationList(BaseModel):
    medications: List[Medication]
