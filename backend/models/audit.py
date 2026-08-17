"""Modelos Pydantic del flujo de auditoria on-chain.

La cola de auditoria y las acciones del auditor operan directamente sobre los
assets de Fabric (no hay tablas audit_cases/dictamenes/corrections en la RDS).
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.models.prescription import Prescription, PrescriptionList

# Acciones del auditor -> estado resultante (validado tambien en el chaincode).
ACCIONES_AUDITORIA = ("revision", "aprobar", "rechazar")


class AuditActionRequest(BaseModel):
    """Datos de entrada para una accion de auditoria."""

    accion: Literal["revision", "aprobar", "rechazar"] = Field(..., title="Acción")
    justificacion: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        title="Justificación de la acción",
    )


class AuditDetail(BaseModel):
    """Detalle de una prescripcion en auditoria: asset + historial on-chain."""

    prescription: Prescription
    history: list[dict] = Field(default_factory=list, title="Historial de transacciones Fabric")


__all__ = [
    "ACCIONES_AUDITORIA",
    "AuditActionRequest",
    "AuditDetail",
    "PrescriptionList",
]
