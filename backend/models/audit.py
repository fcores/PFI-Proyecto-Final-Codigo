"""Modelos Pydantic para el flujo de auditoria, dictamenes y correcciones."""

from datetime import datetime

from pydantic import BaseModel, Field

# Campos clinicos de la prescripcion sobre los que un auditor puede registrar
# una correccion. Debe mantenerse en espejo con CAMPO_OPTIONS de
# frontend/src/pages/AuditCasePage.jsx. Todos deben existir en AuditCase para
# que audit_router pueda leer el valor anterior.
CAMPOS_CORREGIBLES = (
    "diagnostico_cie10",
    "estadio",
    "esquema",
    "id_regimen",
    "dosis_mg_m2",
    "localizacion_tumor",
    "tipo_histologico",
    "linea_tratamiento",
)


class AuditCase(BaseModel):
    """Representacion completa de un caso de auditoria."""

    id: int
    prescription_id: int
    status: str = Field(..., title="Estado del caso")
    assigned_auditor: str | None = None
    created_at: datetime
    prescription_code: str | None = None
    patient_id: int | None = None
    diagnostico_cie10: str | None = None
    estadio: str | None = None
    esquema: str | None = None
    dosis_mg_m2: float | None = None
    superficie_corporal_m2: float | None = None
    id_regimen: str | None = None
    localizacion_tumor: str | None = None
    tipo_histologico: str | None = None
    linea_tratamiento: str | None = None
    estado_validacion: str | None = None
    motivos_validacion: str | None = None
    probabilidad_concordante: float | None = None
    nivel_confianza: str | None = None
    umbral_bajo: float | None = None
    umbral_alto: float | None = None
    origen_validacion: str | None = None
    version_modelo: str | None = None
    features_relevantes: str | None = None
    costo_por_farmaco: str | None = None
    costo_total: float | None = None
    prescription_created_at: datetime | None = None


class AuditCaseList(BaseModel):
    """Lista de casos de auditoria."""

    cases: list[AuditCase]


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
    blockchain_tx_id: str | None = None
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
    blockchain_tx_id: str | None = None
    created_at: datetime


class CorrectionList(BaseModel):
    """Lista de correcciones de un caso."""

    corrections: list[Correction]


class AuditCaseDetail(BaseModel):
    """Detalle completo de un caso: caso + dictamen + correcciones."""

    case: AuditCase
    dictamen: Dictamen | None = None
    corrections: list[Correction] = Field(default_factory=list)
