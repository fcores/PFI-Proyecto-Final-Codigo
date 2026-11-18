"""Servicio de auditoria on-chain.

La cola de auditoria son las prescripciones en estado PENDIENTE_AUDITORIA /
EN_REVISION del world state de Fabric. Las acciones del auditor (revision,
aprobar, rechazar) se asientan con AuditPrescription, que valida la transicion
de estado en el chaincode, encadena un nuevo hash y queda visible para las
tres organizaciones. No hay claim/assignment: cualquier auditor de MedChainMSP
puede dictaminar y su username queda registrado en el evento.
"""

import logging

from backend.blockchain.fabric_client import FabricBusinessError, FabricUnavailableError
from backend.error_handlers import ConflictError, DomainError, NotFoundError
from backend.models.audit import AuditDetail
from backend.models.prescription import Prescription, PrescriptionList
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import ACCION_A_ESTADO
from backend.services.prescription_service import _asset_to_prescription

logger = logging.getLogger(__name__)

ESTADOS_COLA = ("PENDIENTE_AUDITORIA", "EN_REVISION")
# La cola se lee completa de Fabric para poder ordenarla mas recientes primero:
# el chaincode la entrega mas antiguas primero, asi que ordenar solo la primera
# pagina dejaria afuera justamente los casos nuevos.
_PAGINA_COLA = 200
# Resguardo contra un bucle infinito de bookmarks (50 x 200 = 10.000 casos).
_MAX_PAGINAS_COLA = 50


class AuditService:
    """Servicio de auditoria sobre los assets de Fabric."""

    def __init__(self, fabric_repo: FabricPrescriptionRepository) -> None:
        self._repo = fabric_repo

    def queue(self, estado: str = "PENDIENTE_AUDITORIA") -> PrescriptionList:
        """Cola de auditoria completa por estado, mas recientes primero (sin paginar)."""
        try:
            if estado not in ESTADOS_COLA:
                raise DomainError(
                    f"Estado de cola invalido: {estado}. Validos: {', '.join(ESTADOS_COLA)}",
                    status_code=422,
                    error_type="validation_error",
                )
            items = self._leer_cola_completa(estado)
            items.sort(
                key=lambda a: (a.get("created_at") or "", a.get("prescription_id") or ""),
                reverse=True,
            )
            prescriptions = [_asset_to_prescription(item) for item in items]
            return PrescriptionList(prescriptions=prescriptions, bookmark=None, fetched_count=len(prescriptions))
        except Exception as exc:
            logger.error("Error al listar cola de auditoria: %s", exc, exc_info=True)
            raise

    def _leer_cola_completa(self, estado: str) -> list[dict]:
        """Recorre todas las paginas de la cola en Fabric y devuelve los assets."""
        items: list[dict] = []
        bookmark = ""
        for _ in range(_MAX_PAGINAS_COLA):
            pagina = self._repo.list_by_estado(estado, _PAGINA_COLA, bookmark, actor="auditor")
            items.extend(pagina.get("items") or [])
            bookmark = pagina.get("bookmark") or ""
            # CouchDB devuelve un bookmark no vacio aun en la ultima pagina.
            if not bookmark or not pagina.get("items"):
                return items
        logger.error(
            "La cola %s supero %s paginas de %s; se muestra lo leido hasta ahi",
            estado,
            _MAX_PAGINAS_COLA,
            _PAGINA_COLA,
        )
        return items

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
        except FabricUnavailableError as exc:
            # Escritura de resultado incierto (timeout esperando el commit): si
            # el asset ya refleja exactamente esta accion, se informa el exito
            # en lugar de pedirle al auditor que la repita.
            if exc.uncertain:
                recuperada = self._accion_ya_registrada(prescription_id, accion, justificacion, auditor)
                if recuperada is not None:
                    logger.warning(
                        "Accion '%s' sobre %s confirmada releyendo el asset tras un commit incierto",
                        accion,
                        prescription_id,
                    )
                    return recuperada
            raise
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

    def _accion_ya_registrada(
        self,
        prescription_id: str,
        accion: str,
        justificacion: str,
        auditor: str,
    ) -> Prescription | None:
        """Devuelve el asset si su ultimo evento es exactamente esta accion."""
        try:
            asset = self._repo.get(prescription_id, actor="auditor")
        except Exception:
            return None
        if not asset or not asset.get("audit_events"):
            return None
        ultimo = asset["audit_events"][-1]
        coincide = (
            ultimo.get("accion") == accion
            and ultimo.get("auditor") == auditor
            and ultimo.get("justificacion") == justificacion
            and ultimo.get("estado_resultante") == ACCION_A_ESTADO.get(accion)
            and asset.get("estado") == ACCION_A_ESTADO.get(accion)
        )
        if not coincide:
            return None
        return _asset_to_prescription(asset, tx_id=ultimo.get("tx_id"))
