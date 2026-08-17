"""Servicio de auditoria on-chain.

La cola de auditoria son las prescripciones en estado PENDIENTE_AUDITORIA /
EN_REVISION del world state de Fabric. Las acciones del auditor (revision,
aprobar, rechazar) se asientan con AuditPrescription, que valida la transicion
de estado en el chaincode, encadena un nuevo hash y queda visible para las
tres organizaciones. No hay claim/assignment: cualquier auditor de MedChainMSP
puede dictaminar y su username queda registrado en el evento.
"""

import logging

from backend.blockchain.fabric_client import FabricBusinessError
from backend.error_handlers import ConflictError, NotFoundError
from backend.models.audit import AuditDetail
from backend.models.prescription import Prescription, PrescriptionList
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.services.prescription_service import _asset_to_prescription, _paged_to_list

logger = logging.getLogger(__name__)

ESTADOS_COLA = ("PENDIENTE_AUDITORIA", "EN_REVISION")


class AuditService:
    """Servicio de auditoria sobre los assets de Fabric."""

    def __init__(self, fabric_repo: FabricPrescriptionRepository) -> None:
        self._repo = fabric_repo

    def queue(
        self,
        estado: str = "PENDIENTE_AUDITORIA",
        page_size: int = 50,
        bookmark: str = "",
    ) -> PrescriptionList:
        """Cola de auditoria: prescripciones por estado, FIFO."""
        try:
            if estado not in ESTADOS_COLA:
                raise ConflictError(f"Estado de cola invalido: {estado}. Validos: {', '.join(ESTADOS_COLA)}")
            paged = self._repo.list_by_estado(estado, page_size, bookmark, actor="auditor")
            return _paged_to_list(paged)
        except Exception as exc:
            logger.error("Error al listar cola de auditoria: %s", exc, exc_info=True)
            raise

    def detail(self, prescription_id: str) -> AuditDetail:
        """Detalle para el auditor: asset completo + historial de transacciones."""
        try:
            asset = self._repo.get(prescription_id, actor="auditor")
            if asset is None:
                raise NotFoundError(f"Prescripcion {prescription_id} no encontrada")
            history = self._repo.history(prescription_id, actor="auditor")
            return AuditDetail(
                prescription=_asset_to_prescription(asset),
                history=history,
            )
        except Exception as exc:
            logger.error("Error al obtener detalle de auditoria %s: %s", prescription_id, exc, exc_info=True)
            raise

    def accion(
        self,
        prescription_id: str,
        accion: str,
        justificacion: str,
        auditor: str,
    ) -> Prescription:
        """Ejecuta una accion de auditoria y devuelve el asset actualizado.

        El chaincode valida la transicion de estado y que la firma sea de
        MedChainMSP; una transicion invalida se reporta como 409.
        """
        try:
            result = self._repo.audit_action(prescription_id, accion, justificacion, auditor)
            return _asset_to_prescription(result["asset"], tx_id=result["tx_id"])
        except FabricBusinessError as exc:
            message = str(exc)
            if "no encontrada" in message:
                raise NotFoundError(f"Prescripcion {prescription_id} no encontrada") from exc
            if "transicion invalida" in message or "estado actual desconocido" in message:
                raise ConflictError(
                    f"La accion '{accion}' no es valida para el estado actual de la prescripcion"
                ) from exc
            raise
        except Exception as exc:
            logger.error("Error al registrar accion '%s' sobre %s: %s", accion, prescription_id, exc, exc_info=True)
            raise
