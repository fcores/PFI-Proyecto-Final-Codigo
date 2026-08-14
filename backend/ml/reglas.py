"""Capa de reglas deterministicas para deteccion de errores en prescripciones."""

import logging

logger = logging.getLogger(__name__)

UMBRAL_EXCEDENTE_ALTO = 0.20


def aplicar_reglas(datos):
    """Aplica reglas deterministicas de deteccion de errores.

    Recibe un diccionario con los datos de la prescripcion y devuelve
    una lista de motivos de rechazo. Si la lista esta vacia, no se
    detectaron errores por reglas.
    """
    try:
        motivos = []

        ras = datos.get("ras")
        tiene_anti_egfr = datos.get("tiene_anti_egfr", 0)
        if ras == "mutado" and tiene_anti_egfr == 1:
            motivos.append(
                "Contraindicacion: RAS mutado con anti-EGFR. "
                "Los pacientes con mutacion RAS no responden a anti-EGFR."
            )

        msi = datos.get("msi")
        es_inmunoterapia = datos.get("es_inmunoterapia", 0)
        if msi == "MSS" and es_inmunoterapia == 1:
            motivos.append(
                "Contraindicacion: MSS (microsatelite estable) con inmunoterapia. "
                "Solo pacientes MSI-H se benefician de inmunoterapia."
            )

        estadio = datos.get("estadio")
        n_farmacos = datos.get("n_farmacos", 0)
        id_regimen = datos.get("id_regimen")
        if estadio == 1 and n_farmacos > 0 and id_regimen != "R00":
            motivos.append("Estadio I no requiere tratamiento sistemico. " "El regimen debe ser R00 (sin tratamiento).")

        m = datos.get("m")
        if m == "M1" and estadio == 1:
            motivos.append("Inconsistencia: M1 (metastasis) con estadio I. " "Verificar estadificacion.")

        excedente_relativo = datos.get("excedente_relativo", 0)
        if excedente_relativo > UMBRAL_EXCEDENTE_ALTO:
            motivos.append(
                "Excedente de dosis superior al 20%% (%.1f%%). "
                "Revisar la dosificacion prescrita." % (excedente_relativo * 100,)
            )

        return motivos
    except Exception as exc:
        logger.error("Error al aplicar reglas deterministicas: %s", exc, exc_info=True)
        raise
