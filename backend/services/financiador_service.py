"""Panel de lectura del financiador (RF-40).

Agrega, sobre las prescripciones asentadas en Fabric, las palancas de costo
evitado de la tabla de beneficio del financiador: ahorro potencial y efectivo
por alternativas de menor costo, errores detectados por la capa de reglas,
expedientes potencialmente recuperables ante el SURGE y gestiones por estado
del plazo de la Res. SSSalud 951/2025. Lee con la identidad de PrepagaMSP y no
expone datos clinicos de detalle.
"""

import logging
import os

from backend.models.financiador import (
    ConteoPlazos,
    ExpedienteFinanciador,
    ExpedientesFinanciador,
    ResumenFinanciador,
)
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.services.prescription_service import _asset_to_prescription
from backend.services.surge import evaluar_surge

logger = logging.getLogger(__name__)

ACTOR_FINANCIADOR = "prepaga"
TAMANIO_PAGINA = 100
ESTADOS_CERRADOS = ("APROBADA", "RECHAZADA")
# Se usa solo si la variable de entorno falta o es invalida, y se avisa en el
# log: el panel no debe quedar inutilizable por una configuracion incompleta.
TOPE_SIN_CONFIGURAR = 1000


def _tope_prescripciones():
    """Cantidad maxima de prescripciones que el panel lee de Fabric por consulta."""
    try:
        valor = os.getenv("FINANCIADOR_MAX_PRESCRIPCIONES")
        if valor is None or not str(valor).strip().isdigit() or int(valor) <= 0:
            logger.warning(
                "FINANCIADOR_MAX_PRESCRIPCIONES no configurada o invalida; se usa %s.",
                TOPE_SIN_CONFIGURAR,
            )
            return TOPE_SIN_CONFIGURAR
        return int(valor)
    except Exception as exc:
        logger.error("Error al leer el tope de prescripciones del panel: %s", exc, exc_info=True)
        raise


def plazo_vigente(plazos):
    """Plazo que corresponde mirar: el de respuesta hasta que el auditor actua, luego el de resolucion."""
    try:
        if not plazos:
            return None, None
        respuesta = plazos.get("respuesta")
        if respuesta and not respuesta.get("cumplido_en"):
            return "respuesta", respuesta
        resolucion = plazos.get("resolucion")
        if resolucion:
            return "resolucion", resolucion
        return None, None
    except Exception as exc:
        logger.error("Error al determinar el plazo vigente: %s", exc, exc_info=True)
        raise


class FinanciadorService:
    """Servicio del panel del financiador sobre los assets de Fabric."""

    def __init__(self, fabric_repo: FabricPrescriptionRepository) -> None:
        """Inicializa el servicio con el repositorio de Fabric."""
        try:
            self._repo = fabric_repo
        except Exception as exc:
            logger.error("Error al inicializar FinanciadorService: %s", exc, exc_info=True)
            raise

    def _leer_prescripciones(self):
        """Lee las prescripciones de Fabric paginando hasta agotar el ledger o el tope."""
        try:
            tope = _tope_prescripciones()
            prescripciones = []
            bookmark = ""
            alcanzo_tope = False
            while True:
                pagina = self._repo.list(TAMANIO_PAGINA, bookmark, actor=ACTOR_FINANCIADOR)
                for asset in pagina.get("items", []):
                    if len(prescripciones) >= tope:
                        alcanzo_tope = True
                        break
                    prescripciones.append(_asset_to_prescription(asset))
                bookmark = pagina.get("bookmark") or ""
                if alcanzo_tope or not bookmark or not pagina.get("items"):
                    break
            return prescripciones, alcanzo_tope
        except Exception as exc:
            logger.error("Error al leer prescripciones para el panel: %s", exc, exc_info=True)
            raise

    def _expediente(self, prescripcion):
        """Arma la vista del expediente para el financiador."""
        try:
            ml = prescripcion.ml
            surge = ml.surge
            if surge is None:
                surge = evaluar_surge(prescripcion.clinical)
            tipo, plazo = plazo_vigente(prescripcion.plazos)
            ahorro_potencial = ml.ahorro_potencial if ml.requiere_justificacion_costo else None
            return ExpedienteFinanciador(
                prescription_id=prescripcion.prescription_id,
                prescription_code=prescripcion.prescription_code,
                estado=prescripcion.estado,
                created_at=prescripcion.created_at,
                id_regimen=prescripcion.clinical.id_regimen,
                esquema=prescripcion.clinical.esquema,
                veredicto_motor=ml.estado,
                costo_tratamiento=ml.costo_tratamiento,
                ahorro_potencial=ahorro_potencial,
                ahorro_efectivo=ml.ahorro_efectivo,
                regimen_original=ml.regimen_original,
                surge_potencialmente_recuperable=bool(surge.get("potencialmente_recuperable")),
                plazo_tipo=tipo,
                plazo_estado=plazo.get("estado") if plazo else None,
                plazo_vence=plazo.get("vence") if plazo else None,
                plazo_dias_restantes=plazo.get("dias_restantes") if plazo else None,
                plazos=prescripcion.plazos,
            )
        except Exception as exc:
            logger.error(
                "Error al armar el expediente %s para el panel: %s",
                prescripcion.prescription_id,
                exc,
                exc_info=True,
            )
            raise

    def _expedientes(self):
        """Lee las prescripciones y las convierte en expedientes del panel."""
        try:
            prescripciones, alcanzo_tope = self._leer_prescripciones()
            expedientes = []
            for prescripcion in prescripciones:
                expedientes.append((prescripcion, self._expediente(prescripcion)))
            return expedientes, alcanzo_tope
        except Exception as exc:
            logger.error("Error al armar los expedientes del panel: %s", exc, exc_info=True)
            raise

    def resumen(self) -> ResumenFinanciador:
        """Indicadores agregados del panel del financiador."""
        try:
            expedientes, alcanzo_tope = self._expedientes()
            resumen = ResumenFinanciador(
                prescripciones_analizadas=len(expedientes),
                alcanzo_tope=alcanzo_tope,
            )
            conteo_plazos = ConteoPlazos().model_dump()
            for prescripcion, expediente in expedientes:
                ml = prescripcion.ml
                if ml.requiere_justificacion_costo:
                    resumen.alertas_alternativa += 1
                    resumen.ahorro_potencial += float(ml.ahorro_potencial or 0.0)
                if expediente.ahorro_efectivo is not None:
                    resumen.alternativas_adoptadas += 1
                    resumen.ahorro_efectivo += float(expediente.ahorro_efectivo)
                if ml.estado == "RECHAZADO" and ml.origen == "reglas":
                    resumen.errores_detectados += 1
                    if prescripcion.estado == "RECHAZADA":
                        resumen.errores_confirmados += 1
                if expediente.surge_potencialmente_recuperable:
                    resumen.surge_potencialmente_recuperables += 1
                if expediente.plazo_estado in conteo_plazos:
                    conteo_plazos[expediente.plazo_estado] += 1
            resumen.ahorro_potencial = round(resumen.ahorro_potencial, 2)
            resumen.ahorro_efectivo = round(resumen.ahorro_efectivo, 2)
            resumen.plazos = ConteoPlazos(**conteo_plazos)
            return resumen
        except Exception as exc:
            logger.error("Error al calcular el resumen del financiador: %s", exc, exc_info=True)
            raise

    def expedientes(
        self,
        surge: bool | None = None,
        plazo: str | None = None,
        alternativa: str | None = None,
    ) -> ExpedientesFinanciador:
        """Expedientes del panel, filtrables por SURGE, estado de plazo y alternativa.

        alternativa admite 'alerta' (el motor detecto una alternativa mas
        economica) o 'adoptada' (el prescriptor la adopto).
        """
        try:
            expedientes, alcanzo_tope = self._expedientes()
            filtrados = []
            for _prescripcion, expediente in expedientes:
                if surge is not None and expediente.surge_potencialmente_recuperable != surge:
                    continue
                if plazo and expediente.plazo_estado != plazo:
                    continue
                if alternativa == "alerta" and expediente.ahorro_potencial is None:
                    continue
                if alternativa == "adoptada" and expediente.ahorro_efectivo is None:
                    continue
                filtrados.append(expediente)
            return ExpedientesFinanciador(
                expedientes=filtrados,
                total=len(filtrados),
                alcanzo_tope=alcanzo_tope,
            )
        except Exception as exc:
            logger.error("Error al listar los expedientes del financiador: %s", exc, exc_info=True)
            raise
