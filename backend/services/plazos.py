"""Plazos de la Res. SSSalud 951/2025 sobre el circuito de autorizacion.

La resolucion fija dos plazos: 5 dias corridos para responder la solicitud y
30 dias habiles para resolver el procedimiento completo. Se calculan al leer,
a partir de las marcas de tiempo que ya estan en la cadena (alta y eventos de
auditoria), y no se asientan: dependen de la fecha actual.

Los dias habiles se cuentan de lunes a viernes; los feriados nacionales no se
descuentan, de modo que el vencimiento calculado puede adelantarse respecto
del real y nunca lo posterga.
"""

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

DIAS_CORRIDOS_RESPUESTA = 5
DIAS_HABILES_RESOLUCION = 30
DIAS_AVISO = 2
ESTADOS_DICTAMEN = ("APROBADA", "RECHAZADA")
NORMA_PLAZOS = "Res. SSSalud 951/2025"


def parsear_fecha(valor):
    """Convierte un timestamp RFC3339 de la cadena en un datetime con zona UTC."""
    try:
        if not valor:
            return None
        fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=UTC)
        return fecha
    except Exception as exc:
        logger.warning("Timestamp invalido para el calculo de plazos (%s): %s", valor, exc)
        return None


def sumar_dias_habiles(fecha, cantidad):
    """Suma una cantidad de dias habiles (lunes a viernes) a la fecha dada."""
    try:
        resultado = fecha
        sumados = 0
        while sumados < cantidad:
            resultado = resultado + timedelta(days=1)
            if resultado.weekday() < 5:
                sumados += 1
        return resultado
    except Exception as exc:
        logger.error("Error al sumar dias habiles: %s", exc, exc_info=True)
        raise


def _formatear(fecha):
    """Formatea un datetime como RFC3339 en UTC."""
    try:
        if fecha is None:
            return None
        return fecha.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as exc:
        logger.error("Error al formatear la fecha de un plazo: %s", exc, exc_info=True)
        raise


def evaluar_plazo(vence, cumplido_en, ahora):
    """Clasifica un plazo segun si se cumplio, y cuando, o cuanto falta para su vencimiento."""
    try:
        if cumplido_en is not None:
            estado = "cumplido" if cumplido_en <= vence else "cumplido_fuera_de_plazo"
            return {
                "vence": _formatear(vence),
                "cumplido_en": _formatear(cumplido_en),
                "estado": estado,
                "dias_restantes": None,
            }
        dias_restantes = (vence.date() - ahora.date()).days
        if ahora > vence:
            estado = "vencido"
        elif dias_restantes <= DIAS_AVISO:
            estado = "por_vencer"
        else:
            estado = "en_plazo"
        return {
            "vence": _formatear(vence),
            "cumplido_en": None,
            "estado": estado,
            "dias_restantes": dias_restantes,
        }
    except Exception as exc:
        logger.error("Error al evaluar un plazo: %s", exc, exc_info=True)
        raise


def _primer_evento(audit_events, estados=None):
    """Fecha del primer evento de auditoria, opcionalmente filtrado por estado resultante."""
    try:
        primero = None
        for evento in audit_events or []:
            if isinstance(evento, dict):
                estado = evento.get("estado_resultante")
                marca = evento.get("timestamp")
            else:
                estado = getattr(evento, "estado_resultante", None)
                marca = getattr(evento, "timestamp", None)
            if estados is not None and estado not in estados:
                continue
            fecha = parsear_fecha(marca)
            if fecha is None:
                continue
            if primero is None or fecha < primero:
                primero = fecha
        return primero
    except Exception as exc:
        logger.error("Error al leer los eventos de auditoria: %s", exc, exc_info=True)
        raise


def calcular_plazos(created_at, audit_events, ahora=None):
    """Calcula el plazo de respuesta y el de resolucion de una prescripcion."""
    try:
        inicio = parsear_fecha(created_at)
        if inicio is None:
            return None
        if ahora is None:
            ahora = datetime.now(UTC)

        vence_respuesta = inicio + timedelta(days=DIAS_CORRIDOS_RESPUESTA)
        vence_resolucion = sumar_dias_habiles(inicio, DIAS_HABILES_RESOLUCION)

        return {
            "norma": NORMA_PLAZOS,
            "respuesta": evaluar_plazo(vence_respuesta, _primer_evento(audit_events), ahora),
            "resolucion": evaluar_plazo(
                vence_resolucion,
                _primer_evento(audit_events, ESTADOS_DICTAMEN),
                ahora,
            ),
        }
    except Exception as exc:
        logger.error("Error al calcular los plazos: %s", exc, exc_info=True)
        raise
