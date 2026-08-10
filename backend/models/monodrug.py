from typing import List

from pydantic import BaseModel, Field


class MonodrugBase(BaseModel):
    descripcion: str = Field(..., title="Descripción (nombre de la droga)")


class Monodrug(MonodrugBase):
    id: int
    codigo: str = Field(..., title="Código autogenerado")


class MonodrugList(BaseModel):
    monodrugs: List[Monodrug]
