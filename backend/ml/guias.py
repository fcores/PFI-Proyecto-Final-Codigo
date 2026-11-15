"""Recomendacion de regimen segun guias clinicas (NCCN/AAOC/ESMO)."""

import logging

logger = logging.getLogger(__name__)


def regimen_por_guias(datos):
    """Aplica la jerarquia de las guias y devuelve (id_regimen, base_regimen, reglas_aplicadas).

    Recibe un diccionario con las claves clinicas del paciente
    (estadio, msi, ras, braf_v600e, lateralidad, t, ganglios_examinados,
    lvi, pni, linea_tratamiento) y devuelve la tupla con el regimen
    recomendado, su base y la lista de reglas que se aplicaron.
    """
    try:
        reglas = []
        estadio = datos.get("estadio")
        msi = datos.get("msi")
        ras = datos.get("ras")
        braf = datos.get("braf_v600e")
        lat = datos.get("lateralidad")

        if estadio == 1:
            reglas.append("estadio_I_sin_tto")
            return "R00", "R00", reglas

        if estadio == 2:
            t = datos.get("t", 0)
            ganglios = datos.get("ganglios_examinados")
            lvi = datos.get("lvi")
            pni = datos.get("pni")
            factores = 0
            if t is not None and t >= 4:
                factores += 1
            if ganglios is not None and ganglios < 12:
                factores += 1
            if lvi == 1:
                factores += 1
            if pni == 1:
                factores += 1

            if factores == 0:
                reglas.append("estadio_II_sin_riesgo")
                return "R00", "R00", reglas

            reglas.append("estadio_II_con_%d_factores_riesgo" % factores)
            return "R06", "R06", reglas

        if estadio == 3:
            reglas.append("estadio_III_adyuvancia")
            return "R01", "R01", reglas

        if msi == "MSI-H":
            reglas.append("IV_MSI-H_inmunoterapia")
            return "R09", "R09", reglas

        if braf == "presente":
            reglas.append("IV_BRAF_V600E_dirigido")
            return "R10", "R10", reglas

        if ras == "mutado":
            reglas.append("IV_RAS_mutado_bev")
            return "R07", "R01", reglas

        if lat == "izquierdo":
            reglas.append("IV_WT_izquierdo_antiEGFR")
            return "R08", "R01", reglas
        elif lat == "derecho":
            reglas.append("IV_WT_derecho_bev")
            return "R07", "R01", reglas
        else:
            reglas.append("IV_WT_transverso_bev")
            return "R07", "R01", reglas
    except Exception as exc:
        logger.error("Error al recomendar regimen por guias: %s", exc, exc_info=True)
        raise
