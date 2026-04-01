from typing import List

from pydantic import BaseModel, Field


class MonodrugBase(BaseModel):
    descripcion: str = Field(..., title="Descripción")
    sap_id: str = Field(..., title="ID SAP")


class Monodrug(MonodrugBase):
    id: int


class MonodrugList(BaseModel):
    monodrugs: List[Monodrug]
