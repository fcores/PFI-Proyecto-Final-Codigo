"""Modelos del panel de lectura del financiador (RF-40)."""

from typing import Any

from pydantic import BaseModel, Field


class ConteoPlazos(BaseModel):
    """Gestiones por estado del plazo vigente (Res. SSSalud 951/2025)."""

    en_plazo: int = 0
    por_vencer: int = 0
    vencido: int = 0
    cumplido: int = 0
    cumplido_fuera_de_plazo: int = 0


class ResumenFinanciador(BaseModel):
    """Indicadores agregados de las palancas de costo evitado."""

    prescripciones_analizadas: int = Field(0, title="Prescripciones leídas de Fabric")
    alcanzo_tope: bool = Field(False, title="La lectura se cortó en el tope configurado")
    alertas_alternativa: int = Field(0, title="Prescripciones con alternativa de menor costo")
    ahorro_potencial: float = Field(0.0, title="Ahorro potencial detectado por el motor")
    alternativas_adoptadas: int = Field(0, title="Alternativas adoptadas por el prescriptor")
    ahorro_efectivo: float = Field(0.0, title="Ahorro por alternativas adoptadas")
    errores_detectados: int = Field(0, title="Prescripciones no autorizadas por la capa de reglas")
    errores_confirmados: int = Field(0, title="De esas, rechazadas por el auditor")
    surge_potencialmente_recuperables: int = Field(
        0,
        title="Expedientes potencialmente recuperables ante el SURGE",
    )
    plazos: ConteoPlazos = Field(default_factory=ConteoPlazos)


class ExpedienteFinanciador(BaseModel):
    """Expediente tal como lo ve el financiador, sin datos clínicos de detalle."""

    prescription_id: str
    prescription_code: str
    estado: str
    created_at: str
    id_regimen: str | None = None
    esquema: str | None = None
    veredicto_motor: str | None = None
    costo_tratamiento: float | None = None
    ahorro_potencial: float | None = None
    ahorro_efectivo: float | None = None
    regimen_original: str | None = None
    surge_potencialmente_recuperable: bool = False
    plazo_tipo: str | None = None
    plazo_estado: str | None = None
    plazo_vence: str | None = None
    plazo_dias_restantes: int | None = None
    plazos: dict[str, Any] | None = None


class ExpedientesFinanciador(BaseModel):
    """Listado de expedientes del panel del financiador."""

    expedientes: list[ExpedienteFinanciador]
    total: int
    alcanzo_tope: bool = False
