from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class AgreementBase(BaseModel):
    laboratorio: str
    prestador: str
    medicamento: str
    medicamento_sap: str
    medico_auditor: Optional[str] = None
    fecha_inicial: date
    fecha_final: date
    condicion_recupero: str


class Agreement(AgreementBase):
    id: int
    contrato_filename: Optional[str] = None


class AgreementList(BaseModel):
    agreements: List[Agreement]
