"""Servicio de recomendacion de regimen segun guias clinicas."""
import logging
import math

from backend.ml.codificacion import colapsar_estadio, colapsar_t
from backend.ml.feature_mapper import mapear_lateralidad, mapear_linea
from backend.ml.guias import regimen_por_guias
from backend.ml.regimenes import farmacos_regimen, nombre_regimen
from backend.models.prescription import RecomendacionRequest, RecomendacionResponse

logger = logging.getLogger(__name__)


class RecomendacionService:
    """Envuelve regimen_por_guias para el endpoint de sugerencia."""

    def __init__(self, dosis_service=None) -> None:
        """Inicializa el servicio con el calculador de dosis opcional."""
        try:
            self._dosis_service = dosis_service
        except Exception as exc:
            logger.error("Error al inicializar RecomendacionService: %s", exc, exc_info=True)
            raise

    def recomendar(self, data: RecomendacionRequest) -> RecomendacionResponse:
        """Sugiere un regimen a partir de los datos clinicos del paciente."""
        try:
            datos = {
                "estadio": colapsar_estadio(data.estadio),
                "msi": data.msi,
                "ras": data.ras,
                "braf_v600e": data.braf_v600e,
                "lateralidad": mapear_lateralidad(data.localizacion_tumor),
                "t": colapsar_t(data.t) if data.t else None,
                "ganglios_examinados": data.ganglios_examinados,
                "lvi": data.lvi,
                "pni": data.pni,
                "linea_tratamiento": mapear_linea(data.linea_tratamiento),
            }
            id_regimen, base_regimen, reglas = regimen_por_guias(datos)

            costo_por_farmaco = []
            costo_total = None
            if (
                self._dosis_service is not None
                and data.peso_kg is not None
                and data.talla_cm is not None
            ):
                bsa = math.sqrt((data.talla_cm * data.peso_kg) / 3600.0)
                costo_por_farmaco, costo_total = self._dosis_service.costear_regimen(
                    id_regimen, bsa, data.peso_kg,
                )

            return RecomendacionResponse(
                id_regimen=id_regimen,
                base_regimen=base_regimen,
                nombre_regimen=nombre_regimen(id_regimen),
                reglas_aplicadas=reglas,
                farmacos=farmacos_regimen(id_regimen),
                costo_por_farmaco=costo_por_farmaco,
                costo_total=costo_total,
            )
        except Exception as exc:
            logger.error("Error al recomendar regimen: %s", exc, exc_info=True)
            raise
