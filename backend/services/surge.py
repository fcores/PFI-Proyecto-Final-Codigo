"""Marca de potencial recupero ante el SURGE (Res. SSSalud 731/2023).

El SURGE reemplazo al SUR y reintegra el cancer de colon como enfermedad
modulada: un valor mensual por paciente que cubre todos los medicamentos del
tratamiento, sin listado por farmaco. El Anexo II exige carcinoma colorrectal
avanzado o metastasico, paciente mayor de 18 anios y estado funcional ECOG 0-1.
El prototipo no registra ECOG, de modo que la marca es de recupero *potencial*
y el auditor debe constatarlo antes de presentar la solicitud.
"""

import logging

logger = logging.getLogger(__name__)

NORMA_SURGE = "Res. SSSalud 731/2023, Anexo II"
EDAD_MINIMA_SURGE = 18
CRITERIOS_A_CONSTATAR = ["ECOG 0-1"]


def _valor(clinical, campo):
    """Lee un campo del bloque clinico, sea un dict o un modelo."""
    try:
        if isinstance(clinical, dict):
            return clinical.get(campo)
        return getattr(clinical, campo, None)
    except Exception as exc:
        logger.error("Error al leer el campo %s del bloque clinico: %s", campo, exc, exc_info=True)
        raise


def _es_avanzado_o_metastasico(estadio, m):
    """Indica si el estadio o la categoria M corresponden a enfermedad avanzada."""
    try:
        estadio_norm = str(estadio or "").strip().upper()
        m_norm = str(m or "").strip().upper()
        return estadio_norm.startswith("IV") or m_norm.startswith("M1")
    except Exception as exc:
        logger.error("Error al evaluar el estadio para el SURGE: %s", exc, exc_info=True)
        raise


def evaluar_surge(clinical):
    """Evalua si el expediente es potencialmente recuperable ante el SURGE."""
    try:
        criterios = []
        edad = _valor(clinical, "edad")
        es_adulto = edad is not None and int(edad) >= EDAD_MINIMA_SURGE
        if es_adulto:
            criterios.append("Paciente mayor de 18 años")

        avanzado = _es_avanzado_o_metastasico(_valor(clinical, "estadio"), _valor(clinical, "m"))
        if avanzado:
            criterios.append("Carcinoma colorrectal avanzado o metastásico")

        return {
            "potencialmente_recuperable": es_adulto and avanzado,
            "criterios_cumplidos": criterios,
            "a_constatar": list(CRITERIOS_A_CONSTATAR),
            "norma": NORMA_SURGE,
        }
    except Exception as exc:
        logger.error("Error al evaluar el recupero SURGE: %s", exc, exc_info=True)
        raise
