"""Supresion de datos de pacientes con guarda de retencion (RF-38, RF-39, RNF-21).

La Ley 26.529 (art. 18) obliga a conservar la historia clinica al menos diez
anos, y la Ley 25.326 (art. 16) exceptua la supresion cuando existe esa
obligacion. Por eso la solicitud se registra siempre, pero solo se ejecuta
cuando vence el periodo de retencion contado desde el ultimo acto registrado
en la cadena. La ejecucion anonimiza el PHI fuera de la cadena; los asientos
on-chain no se tocan porque solo referencian al seudonimo patient_id.
"""

import logging
import os
from datetime import UTC, datetime

from backend.error_handlers import DomainError, NotFoundError
from backend.models.suppression import SuppressionList, SuppressionRecord

logger = logging.getLogger(__name__)

_FORMATO_FECHA = "%Y-%m-%dT%H:%M:%SZ"
_PAGINA = 200


def ahora_utc() -> datetime:
    """Fecha y hora actual en UTC, sin zona (como se guarda en la base)."""
    try:
        return datetime.now(UTC).replace(tzinfo=None)
    except Exception as exc:
        logger.error("Error al obtener la hora actual: %s", exc, exc_info=True)
        raise


def sumar_anios(fecha: datetime, anios: int) -> datetime:
    """Suma anios calendario; el 29 de febrero cae en el 28 si el destino no es bisiesto."""
    try:
        try:
            return fecha.replace(year=fecha.year + anios)
        except ValueError:
            return fecha.replace(year=fecha.year + anios, day=28)
    except Exception as exc:
        logger.error("Error al sumar %s anios: %s", anios, exc, exc_info=True)
        raise


def anios_de_retencion() -> int:
    """Lee RETENCION_RECETAS_ANIOS del entorno; exige al menos 10 (RNF-21)."""
    try:
        valor = os.getenv("RETENCION_RECETAS_ANIOS")
        if valor is None or not valor.strip():
            raise DomainError(
                "RETENCION_RECETAS_ANIOS no esta configurada.",
                status_code=503,
                error_type="config_error",
            )
        anios = int(valor)
        if anios < 10:
            raise DomainError(
                "RETENCION_RECETAS_ANIOS debe ser de al menos 10 (Ley 26.529, art. 18).",
                status_code=503,
                error_type="config_error",
            )
        return anios
    except DomainError:
        raise
    except Exception as exc:
        logger.error("RETENCION_RECETAS_ANIOS invalida: %s", exc, exc_info=True)
        raise


class SuppressionService:
    """Registro y ejecucion de solicitudes de supresion de pacientes."""

    def __init__(self, repo, patient_repo, prescription_service) -> None:
        """repo: SuppressionRepository; patient_repo: PatientRepository; prescription_service: lectura on-chain."""
        try:
            self._repo = repo
            self._patient_repo = patient_repo
            self._prescription_service = prescription_service
        except Exception as exc:
            logger.error("Error al inicializar SuppressionService: %s", exc, exc_info=True)
            raise

    def _ultimo_acto(self, patient_id: int) -> datetime | None:
        """Fecha del ultimo acto on-chain del paciente (alta o accion de auditoria)."""
        try:
            ultimo = None
            bookmark = ""
            while True:
                pagina = self._prescription_service.by_patient(patient_id, page_size=_PAGINA, bookmark=bookmark)
                for prescripcion in pagina.prescriptions:
                    fechas = [prescripcion.created_at]
                    for evento in prescripcion.audit_events:
                        fechas.append(evento.timestamp)
                    for texto in fechas:
                        fecha = datetime.strptime(texto, _FORMATO_FECHA)
                        if ultimo is None or fecha > ultimo:
                            ultimo = fecha
                if not pagina.bookmark or pagina.fetched_count < _PAGINA:
                    break
                bookmark = pagina.bookmark
            return ultimo
        except Exception as exc:
            logger.error("Error al obtener el ultimo acto del paciente %s: %s", patient_id, exc, exc_info=True)
            raise

    def _ejecutar(self, solicitud: dict, username: str) -> dict:
        """Anonimiza al paciente y marca la solicitud como ejecutada."""
        try:
            self._patient_repo.anonymize(solicitud["patient_id"], username=username)
            ejecutada = self._repo.mark_executed(solicitud["id"])
            logger.info("Supresion ejecutada para el paciente %s.", solicitud["patient_id"])
            return ejecutada
        except Exception as exc:
            logger.error("Error al ejecutar la supresion %s: %s", solicitud.get("id"), exc, exc_info=True)
            raise

    def solicitar(self, patient_id: int, requested_by: str, motivo: str | None = None) -> SuppressionRecord:
        """Registra la solicitud y la ejecuta en el acto si la retencion ya vencio."""
        try:
            if not self._patient_repo.exists(patient_id):
                raise NotFoundError(f"Paciente {patient_id} no encontrado")
            pendiente = self._repo.find_pending(patient_id)
            if pendiente is not None:
                return SuppressionRecord(**pendiente)

            anios = anios_de_retencion()
            ultimo = self._ultimo_acto(patient_id)
            ahora = ahora_utc()
            if ultimo is None:
                ejecutable_desde = ahora
            else:
                ejecutable_desde = sumar_anios(ultimo, anios)

            solicitud = self._repo.insert(patient_id, requested_by, motivo, ejecutable_desde)
            if ejecutable_desde <= ahora:
                solicitud = self._ejecutar(solicitud, requested_by)
            else:
                logger.info(
                    "Supresion del paciente %s pendiente hasta %s por retencion legal.",
                    patient_id,
                    ejecutable_desde.date(),
                )
            return SuppressionRecord(**solicitud)
        except DomainError:
            raise
        except Exception as exc:
            logger.error("Error al solicitar la supresion del paciente %s: %s", patient_id, exc, exc_info=True)
            raise

    def ejecutar_vencidas(self, username: str) -> SuppressionList:
        """Ejecuta las solicitudes pendientes cuyo periodo de retencion ya vencio."""
        try:
            ejecutadas = []
            for solicitud in self._repo.list_due(ahora_utc()):
                ejecutadas.append(SuppressionRecord(**self._ejecutar(solicitud, username)))
            return SuppressionList(solicitudes=ejecutadas)
        except Exception as exc:
            logger.error("Error al ejecutar las supresiones vencidas: %s", exc, exc_info=True)
            raise

    def listar(self) -> SuppressionList:
        """Lista todas las solicitudes de supresion."""
        try:
            solicitudes = []
            for fila in self._repo.list():
                solicitudes.append(SuppressionRecord(**fila))
            return SuppressionList(solicitudes=solicitudes)
        except Exception as exc:
            logger.error("Error al listar las solicitudes de supresion: %s", exc, exc_info=True)
            raise
