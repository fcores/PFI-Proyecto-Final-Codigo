from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.ml.regimenes import REGIMENES


class FeatureAporte(BaseModel):
    """Aporte de una feature al veredicto del modelo."""

    feature: str = Field(..., title="Nombre de la feature")
    aporte: float = Field(..., title="Aporte al score")


class DosisFarmaco(BaseModel):
    """Dosis prescrita para un farmaco del regimen."""

    monodroga: str = Field(..., max_length=200, title="Monodroga")
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
    # Los topes de largo acotan lo que viaja al registro inmutable: todo este
    # bloque se asienta on-chain y no puede corregirse despues.
    patient_id: int = Field(..., ge=1, title="ID Paciente")
    edad: int = Field(..., ge=0, le=120, title="Edad")
    sexo: str = Field(..., min_length=1, max_length=20, title="Sexo")
    peso_kg: float = Field(..., gt=0, le=400, title="Peso (kg)")
    talla_cm: float = Field(..., gt=0, le=260, title="Talla (cm)")

    diagnostico_cie10: str = Field(..., min_length=1, max_length=16, title="Diagnóstico (CIE-10)")
    localizacion_tumor: str = Field(..., min_length=1, max_length=100, title="Localización del tumor primario")
    tipo_histologico: str = Field(..., min_length=1, max_length=200, title="Tipo histológico")
    t: str = Field(..., min_length=1, max_length=10, title="T (tumor primario)")
    n: str = Field(..., min_length=1, max_length=10, title="N (ganglios regionales)")
    m: str = Field(..., min_length=1, max_length=10, title="M (metástasis a distancia)")
    estadio: str = Field(..., min_length=1, max_length=10, title="Estadio")

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

    linea_tratamiento: str = Field(..., min_length=1, max_length=50, title="Línea de tratamiento")
    id_regimen: str = Field(..., max_length=10, title="ID de régimen")
    esquema: str | None = Field(None, max_length=300, title="Esquema y medicamento prescrito")
    dosis_por_farmaco: list[DosisFarmaco] = Field(
        default_factory=list,
        max_length=20,
        title="Dosis por fármaco",
    )
    dosis_mg_m2: float | None = Field(None, ge=0, title="Dosis (mg/m²) derivada")
    medico_prescriptor: str = Field(..., min_length=1, max_length=200, title="Médico prescriptor")
    matricula: str = Field(..., min_length=1, max_length=50, title="Matrícula")
    justificacion_costo: str | None = Field(
        None,
        min_length=5,
        max_length=2000,
        title="Justificación clínica de la elección económica",
    )

    @field_validator("id_regimen")
    @classmethod
    def _regimen_conocido(cls, value: str) -> str:
        if value not in REGIMENES:
            raise ValueError(f"Régimen desconocido: {value}")
        return value


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
    """Bloque clinico del asset on-chain: los datos de entrada mas la BSA.

    prescriptor_username lo completa el backend con el usuario de la sesion; no
    forma parte de PrescriptionBase, de modo que el cliente no puede fijarlo.
    Es opcional para que los assets anteriores a este campo sigan leyendose (la
    verificacion de hashes trabaja sobre el JSON crudo, no sobre este modelo).
    """

    superficie_corporal_m2: float = Field(..., title="Superficie corporal (m²)")
    prescriptor_username: str | None = Field(None, title="Usuario que registró la prescripción")


class ClinicalRecord(BaseModel):
    """Bloque clinico tal como esta asentado on-chain (modelo de LECTURA).

    Deliberadamente sin las validaciones de PrescriptionBase: el ledger es
    inmutable y guarda assets escritos con reglas anteriores (diagnosticos en
    texto libre, regimenes con otro codigo, etc.). Validar al leer haria que un
    solo asset viejo rompa todos los listados. Las reglas se aplican al crear
    (ClinicalData); al leer se devuelve lo registrado tal cual, incluidos los
    campos que este modelo no declare.
    """

    model_config = ConfigDict(extra="allow")

    patient_id: int | None = None
    edad: int | None = None
    sexo: str | None = None
    peso_kg: float | None = None
    talla_cm: float | None = None
    superficie_corporal_m2: float | None = None
    diagnostico_cie10: str | None = None
    localizacion_tumor: str | None = None
    tipo_histologico: str | None = None
    t: str | None = None
    n: str | None = None
    m: str | None = None
    estadio: str | None = None
    msi: str | None = None
    ras: str | None = None
    braf_v600e: str | None = None
    linea_tratamiento: str | None = None
    id_regimen: str | None = None
    esquema: str | None = None
    dosis_por_farmaco: list[dict[str, Any]] = Field(default_factory=list)
    dosis_mg_m2: float | None = None
    medico_prescriptor: str | None = None
    matricula: str | None = None
    justificacion_costo: str | None = None
    prescriptor_username: str | None = None


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
    clinical: ClinicalRecord = Field(..., title="Datos clínicos (tal como están on-chain)")
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
