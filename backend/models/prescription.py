from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class FeatureAporte(BaseModel):
    """Aporte de una feature al veredicto del modelo."""

    feature: str = Field(..., title="Nombre de la feature")
    aporte: float = Field(..., title="Aporte al score")


class DosisFarmaco(BaseModel):
    """Dosis prescrita para un farmaco del regimen."""

    monodroga: str = Field(..., title="Monodroga")
    dosis_mg: float = Field(..., ge=0, title="Dosis (mg)")


class CostoFarmaco(BaseModel):
    """Costo estimado de un farmaco del regimen segun catalogo."""

    monodroga: str = Field(..., title="Monodroga")
    dosis_mg: float = Field(..., title="Dosis requerida (mg)")
    costo: Optional[float] = Field(None, title="Costo estimado")
    presentaciones_usadas: int = Field(0, title="Cantidad de presentaciones")


class ValidationResult(BaseModel):
    """Resultado de la validacion hibrida reglas + ML."""

    estado: str = Field(..., title="Estado de validación")
    motivos: List[str] = Field(default_factory=list, title="Motivos")
    probabilidad_concordante: Optional[float] = Field(None, title="Probabilidad concordante")
    nivel_confianza: Optional[str] = Field(None, title="Nivel de confianza")
    umbral_bajo: Optional[float] = Field(None, title="Umbral bajo")
    umbral_alto: Optional[float] = Field(None, title="Umbral alto")
    origen: Optional[str] = Field(None, title="Origen del veredicto")
    version_modelo: Optional[str] = Field(None, title="Versión del modelo")
    features_relevantes: List[FeatureAporte] = Field(
        default_factory=list,
        title="Features relevantes",
    )
    regimen_sugerido: Optional[str] = Field(None, title="Régimen sugerido por guías")
    reglas_guias: List[str] = Field(default_factory=list, title="Reglas de guías aplicadas")
    costo_por_farmaco: List[CostoFarmaco] = Field(
        default_factory=list,
        title="Costo por fármaco",
    )
    costo_total: Optional[float] = Field(None, title="Costo total estimado")


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

    msi: Literal["MSI-H", "MSS", "no_evaluado"] = Field(
        "no_evaluado",
        title="Estado MSI",
    )
    ras: Literal["wild_type", "mutado", "no_evaluado"] = Field(
        "no_evaluado",
        title="Estado RAS",
    )
    braf_v600e: Literal["presente", "wild_type", "no_evaluado"] = Field(
        "no_evaluado",
        title="Estado BRAF V600E",
    )

    linea_tratamiento: str = Field(..., title="Línea de tratamiento")
    id_regimen: str = Field(..., title="ID de régimen")
    esquema: Optional[str] = Field(None, title="Esquema y medicamento prescrito")
    dosis_por_farmaco: List[DosisFarmaco] = Field(
        default_factory=list,
        title="Dosis por fármaco",
    )
    dosis_mg_m2: Optional[float] = Field(None, title="Dosis (mg/m²) derivada")
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


class RecomendacionRequest(BaseModel):
    """Datos clinicos para sugerir regimen segun guias."""

    edad: Optional[int] = None
    sexo: Optional[str] = None
    estadio: str = Field(..., title="Estadio")
    t: Optional[str] = None
    n: Optional[str] = None
    m: Optional[str] = None
    localizacion_tumor: Optional[str] = None
    msi: Literal["MSI-H", "MSS", "no_evaluado"] = "no_evaluado"
    ras: Literal["wild_type", "mutado", "no_evaluado"] = "no_evaluado"
    braf_v600e: Literal["presente", "wild_type", "no_evaluado"] = "no_evaluado"
    linea_tratamiento: Optional[str] = None
    ganglios_examinados: Optional[int] = None
    lvi: Optional[int] = None
    pni: Optional[int] = None
    peso_kg: Optional[float] = Field(None, gt=0, title="Peso (kg)")
    talla_cm: Optional[float] = Field(None, gt=0, title="Talla (cm)")


class RecomendacionResponse(BaseModel):
    """Respuesta de recomendacion de regimen por guias."""

    id_regimen: str
    base_regimen: str
    nombre_regimen: str
    reglas_aplicadas: List[str]
    farmacos: List[str]
    costo_por_farmaco: List[CostoFarmaco] = Field(
        default_factory=list,
        title="Costo por fármaco",
    )
    costo_total: Optional[float] = Field(None, title="Costo total estimado")
