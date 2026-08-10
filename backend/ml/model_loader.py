"""Carga perezosa y cacheada del artefacto LightGBM."""
import logging
import os
from pathlib import Path

import joblib

logger = logging.getLogger(__name__)

_ARTEFACTO = None
_CARGA_INTENTADA = False


def _ruta_default():
    """Construye la ruta por defecto del artefacto dentro del repositorio."""
    try:
        return (
            Path(__file__).resolve().parent.parent.parent
            / "ml_models"
            / "artefactos"
            / "modelo_gbm.joblib"
        )
    except Exception as exc:
        logger.error("Error al construir ruta default del modelo: %s", exc, exc_info=True)
        raise


def cargar_modelo():
    """Carga el artefacto del modelo una sola vez.

    Lee ML_MODEL_PATH sin valor por defecto (criterio 12). Si la variable no
    esta definida, usa la ruta relativa a ml_models/artefactos. Si el archivo
    no existe, retorna None para degradar a solo-reglas.
    """
    global _ARTEFACTO, _CARGA_INTENTADA
    try:
        if _CARGA_INTENTADA:
            return _ARTEFACTO

        _CARGA_INTENTADA = True
        ruta_env = os.getenv("ML_MODEL_PATH")
        if ruta_env:
            ruta = Path(ruta_env)
        else:
            ruta = _ruta_default()
            logger.warning(
                "ML_MODEL_PATH no definida; se usa ruta por defecto %s",
                ruta,
            )

        if not ruta.exists():
            logger.error("Artefacto de modelo no encontrado en %s", ruta)
            _ARTEFACTO = None
            return None

        _ARTEFACTO = joblib.load(ruta)
        logger.info(
            "Modelo cargado: version=%s features=%s",
            _ARTEFACTO.get("version_modelo"),
            len(_ARTEFACTO.get("features", [])),
        )
        return _ARTEFACTO
    except Exception as exc:
        logger.error("Error al cargar modelo ML: %s", exc, exc_info=True)
        _ARTEFACTO = None
        return None


def modelo_disponible():
    """Indica si el artefacto esta cargado y usable."""
    try:
        artefacto = cargar_modelo()
        return artefacto is not None and artefacto.get("model") is not None
    except Exception as exc:
        logger.error("Error al verificar disponibilidad del modelo: %s", exc, exc_info=True)
        return False
