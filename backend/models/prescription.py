from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    estado: str = Field(..., title="Estado de validación")
    motivos: List[str] = Field(default_factory=list, title="Motivos")


class PrescriptionBase(BaseModel):
    patient_sap_id: str = Field(..., title="ID Paciente SAP")
    edad: int = Field(..., ge=0, le=120, title="Edad")
    sexo: str = Field(..., title="Sexo")
    peso_kg: float = Field(..., gt=0, title="Peso (kg)")
    talla_cm: float = Field(..., gt=0, title="Talla (cm)")

    diagnostico_cie10: str = Field(..., title="Diagnóstico (CIE-10)")
    localizacion_tumor: str = Field(..., title="Localización del tumor primario")
    tipo_histologico: str = Field(..., title="Tipo histológico")
    t: str = Field(..., title="T (tumor primario)")
    n: str = Field(..., title="N (ganglios regionales)")
    m: str = Field(..., title="M (metástasis a distancia)")
    estadio: str = Field(..., title="Estadio")

    msi_alta: bool = Field(False, title="Inestabilidad microsatelital alta")
    ras_mutado: bool = Field(False, title="Mutación RAS")
    braf_v600e: bool = Field(False, title="Mutación BRAF V600E")

    linea_tratamiento: str = Field(..., title="Línea de tratamiento")
    esquema: str = Field(..., title="Esquema y medicamento prescrito")
    dosis_mg_m2: float = Field(..., gt=0, title="Dosis (mg/m²)")
    medico_prescriptor: str = Field(..., title="Médico prescriptor")
    matricula: str = Field(..., title="Matrícula")


class Prescription(PrescriptionBase):
    id: int
    prescription_code: str = Field(..., title="Código de prescripción")
    superficie_corporal_m2: float = Field(..., title="Superficie corporal (m²)")
    created_at: datetime = Field(..., title="Fecha de creación")
    validacion: ValidationResult = Field(..., title="Resultado de validación")
    blockchain_tx_id: Optional[str] = Field(None, title="ID de transacción en blockchain")
    block_index: Optional[int] = Field(None, title="Índice del bloque en el ledger")


class PrescriptionList(BaseModel):
    prescriptions: List[Prescription]
