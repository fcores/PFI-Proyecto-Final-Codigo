from typing import Literal

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
    costo: float | None = Field(None, title="Costo estimado")
    presentaciones_usadas: int = Field(0, title="Cantidad de presentaciones")


class AlternativaEconomica(BaseModel):
    """Regimen terapeuticamente equivalente con menor costo de tratamiento."""

    id_regimen: str = Field(..., title="ID de régimen alternativo")
    nombre: str = Field(..., title="Nombre del régimen alternativo")
    costo_tratamiento: float = Field(..., title="Costo del tratamiento completo")
    ahorro: float = Field(..., title="Ahorro frente al prescrito")
    pct_ahorro: float = Field(..., title="Ahorro porcentual")
    ciclos: int = Field(..., title="Ciclos del esquema estándar")


class ValidationResult(BaseModel):
    """Resultado de la validacion hibrida reglas + ML."""

    estado: str = Field(..., title="Estado de validación")
    motivos: list[str] = Field(default_factory=list, title="Motivos")
    probabilidad_concordante: float | None = Field(None, title="Probabilidad concordante")
    nivel_confianza: str | None = Field(None, title="Nivel de confianza")
    umbral_bajo: float | None = Field(None, title="Umbral bajo")
    umbral_alto: float | None = Field(None, title="Umbral alto")
    origen: str | None = Field(None, title="Origen del veredicto")
    version_modelo: str | None = Field(None, title="Versión del modelo")
    features_relevantes: list[FeatureAporte] = Field(
        default_factory=list,
        title="Features relevantes",
    )
    regimen_sugerido: str | None = Field(None, title="Régimen sugerido por guías")
    reglas_guias: list[str] = Field(default_factory=list, title="Reglas de guías aplicadas")
    costo_por_farmaco: list[CostoFarmaco] = Field(
        default_factory=list,
        title="Costo por fármaco",
    )
    costo_total: float | None = Field(None, title="Costo total estimado")
    costo_tratamiento: float | None = Field(
        None,
        title="Costo del tratamiento completo",
    )
    alternativas_economicas: list[AlternativaEconomica] = Field(
        default_factory=list,
        title="Alternativas equivalentes de menor costo",
    )
    ahorro_potencial: float | None = Field(None, title="Ahorro potencial")
    requiere_justificacion_costo: bool = Field(
        False,
        title="Exige justificación económica del prescriptor",
    )


class PrescriptionBase(BaseModel):
    patient_id: int = Field(..., title="ID Paciente")
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
    esquema: str | None = Field(None, title="Esquema y medicamento prescrito")
    dosis_por_farmaco: list[DosisFarmaco] = Field(
        default_factory=list,
        title="Dosis por fármaco",
    )
    dosis_mg_m2: float | None = Field(None, title="Dosis (mg/m²) derivada")
    medico_prescriptor: str = Field(..., title="Médico prescriptor")
    matricula: str = Field(..., title="Matrícula")
    justificacion_costo: str | None = Field(
        None,
        min_length=5,
        max_length=2000,
        title="Justificación clínica de la elección económica",
    )


# Veredictos posibles del motor hibrido reglas + ML (soporte de decision).
ESTADOS_VALIDACION_ML = (
    "APROBADO",
    "RECHAZADO",
    "REVISION",
)

# Ciclo de vida on-chain de la prescripcion (lo administra el chaincode).
ESTADOS_PRESCRIPCION = (
    "PENDIENTE_AUDITORIA",
    "EN_REVISION",
    "APROBADA",
    "RECHAZADA",
)


class ClinicalData(PrescriptionBase):
    """Bloque clinico del asset on-chain: los datos de entrada mas la BSA."""

    superficie_corporal_m2: float = Field(..., title="Superficie corporal (m²)")


class AuditEvent(BaseModel):
    """Eslabon de la cadena de auditoria de una prescripcion on-chain."""

    seq: int
    accion: str
    estado_resultante: str
    auditor: str
    justificacion: str
    timestamp: str
    tx_id: str
    prev_hash: str
    event_hash: str


class Prescription(BaseModel):
    """Asset on-chain de una prescripcion. Vive SOLO en Fabric (sin copia en RDS).

    Ciclo de vida (validado por el chaincode):
    PENDIENTE_AUDITORIA - toda prescripcion nace pendiente; el veredicto del
                          motor ML (bloque `ml`) es soporte de decision.
    EN_REVISION         - el auditor la marco en revision.
    APROBADA/RECHAZADA  - dictamen final del auditor (estados terminales).
    """

    prescription_id: str = Field(..., title="ID (ULID)")
    prescription_code: str = Field(..., title="Código de prescripción")
    estado: str = Field(..., title="Estado del ciclo de auditoría")
    clinical: ClinicalData = Field(..., title="Datos clínicos")
    ml: ValidationResult = Field(..., title="Veredicto del motor reglas + ML")
    created_at: str = Field(..., title="Fecha de creación (RFC3339)")
    created_by_msp: str | None = Field(None, title="MSP que creó el asset")
    payload_hash: str = Field(..., title="SHA-256 del payload canónico")
    current_hash: str = Field(..., title="Último eslabón de la cadena de hashes")
    audit_events: list[AuditEvent] = Field(default_factory=list, title="Eventos de auditoría")
    tx_id: str | None = Field(None, title="TxID de Fabric de la última escritura conocida")


class PrescriptionList(BaseModel):
    prescriptions: list[Prescription]
    bookmark: str | None = Field(None, title="Bookmark para la página siguiente")
    fetched_count: int = Field(0, title="Cantidad de resultados de esta página")


class VerifyResult(BaseModel):
    """Resultado de la verificación externa de la cadena de hashes."""

    prescription_id: str
    valido: bool
    errores: list[str] = Field(default_factory=list)
    payload_hash: str | None = None
    current_hash: str | None = None


class RecomendacionRequest(BaseModel):
    """Datos clinicos para sugerir regimen segun guias."""

    edad: int | None = None
    sexo: str | None = None
    estadio: str = Field(..., title="Estadio")
    t: str | None = None
    n: str | None = None
    m: str | None = None
    localizacion_tumor: str | None = None
    msi: Literal["MSI-H", "MSS", "no_evaluado"] = "no_evaluado"
    ras: Literal["wild_type", "mutado", "no_evaluado"] = "no_evaluado"
    braf_v600e: Literal["presente", "wild_type", "no_evaluado"] = "no_evaluado"
    linea_tratamiento: str | None = None
    ganglios_examinados: int | None = None
    lvi: int | None = None
    pni: int | None = None
    peso_kg: float | None = Field(None, gt=0, title="Peso (kg)")
    talla_cm: float | None = Field(None, gt=0, title="Talla (cm)")


class RecomendacionResponse(BaseModel):
    """Respuesta de recomendacion de regimen por guias."""

    id_regimen: str
    base_regimen: str
    nombre_regimen: str
    reglas_aplicadas: list[str]
    farmacos: list[str]
    costo_por_farmaco: list[CostoFarmaco] = Field(
        default_factory=list,
        title="Costo por fármaco",
    )
    costo_total: float | None = Field(None, title="Costo total estimado")
