"""Funciones puras de calculo de dosis y resolucion de presentaciones."""

import logging
from itertools import combinations_with_replacement

from backend.ml.regimenes import DOSIS_REFERENCIA, FARMACOS_ORALES

logger = logging.getLogger(__name__)


def calcular_dosis_mg(farmaco, bsa, peso_kg, regimen_id):
    """Calcula la dosis total en mg segun la base correcta (BSA, peso o fija)."""
    try:
        info = DOSIS_REFERENCIA.get(farmaco)
        if info is None:
            return 0.0

        if info["base"] == "bsa":
            mg_m2 = info["mg_m2"]
            if farmaco == "oxaliplatino" and regimen_id == "R02":
                mg_m2 = info.get("regimen_capeox_mg_m2", mg_m2)
            return mg_m2 * bsa
        elif info["base"] == "peso":
            return info["mg_kg"] * peso_kg
        elif info["base"] == "fija":
            return info["mg"]
        return 0.0
    except Exception as exc:
        logger.error("Error al calcular dosis de %s: %s", farmaco, exc, exc_info=True)
        raise


def resolver_presentaciones(dosis_mg, farmaco, presentaciones):
    """Resuelve la cobertura entera de minimo excedente.

    Recibe la lista de presentaciones como argumento (no la lee de ningun
    repositorio). Cada presentacion es un dict con claves 'potencia_mg',
    'precio', 'ean' y opcionalmente 'via'.
    """
    try:
        if not presentaciones:
            return {"mg_cubiertos": 0, "excedente_mg": dosis_mg, "presentaciones": [], "costo": 0}

        es_oral = farmaco in FARMACOS_ORALES

        pres_filtradas = []
        for p in presentaciones:
            if p.get("potencia_mg") is None or p.get("precio") is None:
                continue
            via = str(p.get("via", "")).upper()
            if es_oral:
                if via and "ORAL" not in via and "INYECT" in via:
                    continue
            else:
                if via and "ORAL" in via and "INYECT" not in via:
                    continue
            pres_filtradas.append(p)

        if not pres_filtradas:
            return {"mg_cubiertos": 0, "excedente_mg": dosis_mg, "presentaciones": [], "costo": 0}

        potencias_vistas = {}
        for p in pres_filtradas:
            pot = p["potencia_mg"]
            if pot not in potencias_vistas or p["precio"] < potencias_vistas[pot]["precio"]:
                potencias_vistas[pot] = p

        potencias_list = sorted(potencias_vistas.values(), key=lambda x: -x["potencia_mg"])

        mejor = None
        req = dosis_mg

        for max_units in range(1, 20):
            for combo in combinations_with_replacement(potencias_list, max_units):
                total_mg = sum(p["potencia_mg"] for p in combo)
                if total_mg >= req:
                    excedente = total_mg - req
                    costo = sum(p["precio"] for p in combo)
                    if (
                        mejor is None
                        or excedente < mejor["excedente"]
                        or (excedente == mejor["excedente"] and costo < mejor["costo"])
                    ):
                        mejor = {"mg": total_mg, "excedente": excedente, "costo": costo, "combo": combo}
            if mejor is not None and mejor["excedente"] == 0:
                break
            if mejor is not None:
                break

        if mejor is None:
            return {"mg_cubiertos": 0, "excedente_mg": dosis_mg, "presentaciones": [], "costo": 0}

        return {
            "mg_cubiertos": mejor["mg"],
            "excedente_mg": mejor["excedente"],
            "presentaciones": [{"ean": p.get("ean", ""), "potencia_mg": p["potencia_mg"]} for p in mejor["combo"]],
            "costo": mejor["costo"],
        }
    except Exception as exc:
        logger.error("Error al resolver presentaciones de %s: %s", farmaco, exc, exc_info=True)
        raise
