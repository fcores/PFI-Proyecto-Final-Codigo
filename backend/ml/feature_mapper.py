"""Traduce PrescriptionBase a las 21 features del modelo."""
import logging

from backend.ml.codificacion import (
    FEATURES_CATEGORICAS_MODELO,
    FEATURES_MODELO,
    colapsar_estadio,
    colapsar_m,
    colapsar_n,
    colapsar_t,
    histologia_agrupada,
    preparar_features,
)
from backend.ml.regimenes import flags_regimen

logger = logging.getLogger(__name__)

MAPA_SEXO = {
    "masculino": "male",
    "male": "male",
    "m": "male",
    "femenino": "female",
    "female": "female",
    "f": "female",
}

MAPA_LATERALIDAD = {
    "colon derecho": "derecho",
    "derecho": "derecho",
    "colon izquierdo": "izquierdo",
    "izquierdo": "izquierdo",
    "colon transverso": "transverso",
    "transverso": "transverso",
}

MAPA_LINEA = {
    "primera": 1,
    "1": 1,
    "segunda": 2,
    "2": 2,
    "tercera": 3,
    "3": 3,
}


def mapear_sexo(valor):
    """Normaliza el sexo del formulario al vocabulario del modelo."""
    try:
        if valor is None:
            return None
        return MAPA_SEXO.get(str(valor).strip().lower())
    except Exception as exc:
        logger.error("Error al mapear sexo '%s': %s", valor, exc, exc_info=True)
        raise


def mapear_lateralidad(valor):
    """Normaliza la localizacion del tumor a lateralidad del modelo."""
    try:
        if valor is None:
            return None
        return MAPA_LATERALIDAD.get(str(valor).strip().lower())
    except Exception as exc:
        logger.error("Error al mapear lateralidad '%s': %s", valor, exc, exc_info=True)
        raise


def mapear_linea(valor):
    """Normaliza la linea de tratamiento a entero 1/2/3."""
    try:
        if valor is None:
            return 1
        if isinstance(valor, (int, float)):
            return int(valor)
        return MAPA_LINEA.get(str(valor).strip().lower(), 1)
    except Exception as exc:
        logger.error("Error al mapear linea '%s': %s", valor, exc, exc_info=True)
        raise


def _farmacos_desde_dosis(dosis_por_farmaco):
    """Extrae nombres de monodroga desde dosis_por_farmaco."""
    try:
        farmacos = []
        for item in dosis_por_farmaco or []:
            if hasattr(item, "monodroga"):
                farmacos.append(item.monodroga)
            elif isinstance(item, dict):
                farmacos.append(item.get("monodroga"))
        return [f for f in farmacos if f]
    except Exception as exc:
        logger.error("Error al extraer farmacos de dosis: %s", exc, exc_info=True)
        raise


def prescription_a_datos_modelo(data, superficie_corporal_m2, excedente_relativo):
    """Convierte una PrescriptionBase (o dict compatible) al dict crudo del modelo."""
    try:
        if hasattr(data, "model_dump"):
            raw = data.model_dump()
        else:
            raw = dict(data)

        id_regimen = raw.get("id_regimen")
        farmacos = _farmacos_desde_dosis(raw.get("dosis_por_farmaco"))
        if farmacos:
            flags = flags_regimen(id_regimen, farmacos=farmacos)
        else:
            flags = flags_regimen(id_regimen)

        datos = {
            "edad": raw.get("edad"),
            "t": colapsar_t(raw.get("t")),
            "n": colapsar_n(raw.get("n")),
            "estadio": colapsar_estadio(raw.get("estadio")),
            "superficie_corporal_m2": superficie_corporal_m2,
            "peso_kg": raw.get("peso_kg"),
            "n_farmacos": flags["n_farmacos"],
            "tiene_anti_egfr": flags["tiene_anti_egfr"],
            "tiene_antiangiogenico": flags["tiene_antiangiogenico"],
            "es_inmunoterapia": flags["es_inmunoterapia"],
            "es_dirigido": flags["es_dirigido"],
            "excedente_relativo": excedente_relativo,
            "linea_tratamiento": mapear_linea(raw.get("linea_tratamiento")),
            "sexo": mapear_sexo(raw.get("sexo")),
            "lateralidad": mapear_lateralidad(raw.get("localizacion_tumor")),
            "histologia": histologia_agrupada(raw.get("tipo_histologico")),
            "msi": raw.get("msi"),
            "ras": raw.get("ras"),
            "braf_v600e": raw.get("braf_v600e"),
            "m": colapsar_m(raw.get("m")),
            "id_regimen": id_regimen,
        }
        return datos
    except Exception as exc:
        logger.error("Error al mapear prescription a datos modelo: %s", exc, exc_info=True)
        raise


def prescription_a_features(data, superficie_corporal_m2, excedente_relativo, orden_features=None):
    """Devuelve la lista ordenada de features numericas listas para predecir."""
    try:
        datos = prescription_a_datos_modelo(data, superficie_corporal_m2, excedente_relativo)
        encoded = preparar_features(datos)
        if orden_features is None:
            orden_features = FEATURES_MODELO + FEATURES_CATEGORICAS_MODELO
        return [encoded.get(col, -1) for col in orden_features], datos
    except Exception as exc:
        logger.error("Error al generar features de prescription: %s", exc, exc_info=True)
        raise
