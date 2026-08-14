"""Modelos Pydantic para el flujo de auditoria, dictamenes y correcciones."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AuditCase(BaseModel):
    """Representacion completa de un caso de auditoria."""

    id: int
    prescription_id: int
    status: str = Field(..., title="Estado del caso")
    assigned_auditor: Optional[str] = None
    created_at: datetime
    prescription_code: Optional[str] = None
    patient_id: Optional[int] = None
    diagnostico_cie10: Optional[str] = None
    estadio: Optional[str] = None
    esquema: Optional[str] = None
    dosis_mg_m2: Optional[float] = None
    superficie_corporal_m2: Optional[float] = None
    id_regimen: Optional[str] = None
    estado_validacion: Optional[str] = None
    motivos_validacion: Optional[str] = None
    probabilidad_concordante: Optional[float] = None
    nivel_confianza: Optional[str] = None
    umbral_bajo: Optional[float] = None
    umbral_alto: Optional[float] = None
    origen_validacion: Optional[str] = None
    version_modelo: Optional[str] = None
    features_relevantes: Optional[str] = None
    prescription_created_at: Optional[datetime] = None


class AuditCaseList(BaseModel):
    """Lista de casos de auditoria."""

    cases: List[AuditCase]


class DictamenRequest(BaseModel):
    """Datos de entrada para emitir un dictamen."""

    resultado: str = Field(..., title="Resultado del dictamen")
    justificacion: str = Field(..., title="Justificacion del dictamen")


class Dictamen(BaseModel):
    """Representacion completa de un dictamen emitido."""

    id: int
    audit_case_id: int
    resultado: str
    justificacion: str
    auditor_username: str
    blockchain_tx_id: Optional[str] = None
    created_at: datetime


class CorrectionRequest(BaseModel):
    """Datos de entrada para registrar una correccion."""

    campo: str = Field(..., title="Campo a corregir")
    valor_nuevo: str = Field(..., title="Nuevo valor")
    justificacion: str = Field(..., title="Justificacion de la correccion")


class Correction(BaseModel):
    """Representacion completa de una correccion de dato clinico."""

    id: int
    audit_case_id: int
    campo: str
    valor_anterior: str
    valor_nuevo: str
    justificacion: str
    auditor_username: str
    blockchain_tx_id: Optional[str] = None
    created_at: datetime


class CorrectionList(BaseModel):
    """Lista de correcciones de un caso."""

    corrections: List[Correction]


class AuditCaseDetail(BaseModel):
    """Detalle completo de un caso: caso + dictamen + correcciones."""

    case: AuditCase
    dictamen: Optional[Dictamen] = None
    corrections: List[Correction] = Field(default_factory=list)
