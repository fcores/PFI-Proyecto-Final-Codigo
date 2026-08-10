"""Servicio de auditoria: gestiona cola, dictamenes y correcciones."""
import logging

from backend.models.audit import (
    AuditCase,
    AuditCaseDetail,
    AuditCaseList,
    Correction,
    CorrectionList,
    Dictamen,
)
from backend.repositories.audit_repo import AuditRepository
from backend.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)


class AuditService:
    """Servicio de auditoria: gestiona cola, dictamenes y correcciones."""

    def __init__(self, repo: AuditRepository, ledger_service: LedgerService) -> None:
        """Inicializa el servicio de auditoria."""
        try:
            self._repo = repo
            self._ledger = ledger_service
        except Exception as exc:
            logger.error("Error al inicializar AuditService: %s", exc, exc_info=True)
            raise

    def list_pending(self) -> AuditCaseList:
        """Lista los casos pendientes de revision."""
        try:
            cases = self._repo.list_pending()
            return AuditCaseList(cases=cases)
        except Exception as exc:
            logger.error("Error al listar casos pendientes: %s", exc, exc_info=True)
            raise

    def get_case_detail(self, case_id: int) -> AuditCaseDetail:
        """Obtiene el detalle completo de un caso de auditoria."""
        try:
            case = self._repo.find_case_by_id(case_id)
            if case is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Caso de auditoria no encontrado.")
            dictamen = self._repo.find_dictamen_by_case(case_id)
            corrections = self._repo.list_corrections_by_case(case_id)
            return AuditCaseDetail(case=case, dictamen=dictamen, corrections=corrections)
        except Exception as exc:
            logger.error("Error al obtener detalle del caso %s: %s", case_id, exc, exc_info=True)
            raise

    def create_dictamen(
        self, case_id: int, resultado: str, justificacion: str, auditor_username: str,
    ) -> Dictamen:
        """Registra un dictamen para un caso de auditoria."""
        try:
            payload = {
                "audit_case_id": case_id,
                "resultado": resultado,
                "justificacion": justificacion,
                "auditor": auditor_username,
            }
            block = self._ledger.append("dictamen", payload)

            dictamen = self._repo.add_dictamen(
                case_id, resultado, justificacion, auditor_username, block.hash,
            )

            new_status = "dictaminado"
            self._repo.update_case_status(case_id, new_status, auditor_username)

            return dictamen
        except Exception as exc:
            logger.error("Error al crear dictamen para caso %s: %s", case_id, exc, exc_info=True)
            raise

    def create_correction(
        self, case_id: int, campo: str, valor_anterior: str,
        valor_nuevo: str, justificacion: str, auditor_username: str,
    ) -> Correction:
        """Registra una correccion de dato clinico."""
        try:
            payload = {
                "audit_case_id": case_id,
                "campo": campo,
                "valor_anterior": valor_anterior,
                "valor_nuevo": valor_nuevo,
                "auditor": auditor_username,
            }
            block = self._ledger.append("correction", payload)

            correction = self._repo.add_correction(
                case_id, campo, valor_anterior, valor_nuevo,
                justificacion, auditor_username, block.hash,
            )
            return correction
        except Exception as exc:
            logger.error("Error al crear correccion para caso %s: %s", case_id, exc, exc_info=True)
            raise

    def list_corrections(self, case_id: int) -> CorrectionList:
        """Lista las correcciones de un caso."""
        try:
            corrections = self._repo.list_corrections_by_case(case_id)
            return CorrectionList(corrections=corrections)
        except Exception as exc:
            logger.error("Error al listar correcciones del caso %s: %s", case_id, exc, exc_info=True)
            raise
