"""Catalogos de regimenes, dosis de referencia y monodrogas para cancer de colon."""
import logging

logger = logging.getLogger(__name__)

REGIMENES = {
    "R00": {"nombre": "Sin tratamiento sistemico", "farmacos": []},
    "R01": {"nombre": "mFOLFOX6", "farmacos": ["oxaliplatino", "fluorouracilo", "leucovorina"]},
    "R02": {"nombre": "CAPEOX", "farmacos": ["oxaliplatino", "capecitabina"]},
    "R03": {"nombre": "FOLFIRI", "farmacos": ["irinotecan", "fluorouracilo", "leucovorina"]},
    "R04": {"nombre": "FOLFOXIRI", "farmacos": ["oxaliplatino", "irinotecan", "fluorouracilo", "leucovorina"]},
    "R05": {"nombre": "5-FU/LV", "farmacos": ["fluorouracilo", "leucovorina"]},
    "R06": {"nombre": "Capecitabina mono", "farmacos": ["capecitabina"]},
    "R07": {"nombre": "Base + Bevacizumab", "farmacos": ["bevacizumab"]},
    "R08": {"nombre": "Base + Anti-EGFR", "farmacos": ["cetuximab"]},
    "R09": {"nombre": "Pembrolizumab", "farmacos": ["pembrolizumab"]},
    "R10": {"nombre": "Encorafenib + Anti-EGFR", "farmacos": ["encorafenib", "cetuximab"]},
    "R11": {"nombre": "Ipilimumab + Nivolumab", "farmacos": ["ipilimumab", "nivolumab"]},
    "R12": {"nombre": "Regorafenib", "farmacos": ["regorafenib"]},
    "R13": {"nombre": "Trifluridina/tipiracilo", "farmacos": ["trifluridina_tipiracilo"]},
}

DOSIS_REFERENCIA = {
    "oxaliplatino": {"base": "bsa", "mg_m2": 85, "regimen_capeox_mg_m2": 130},
    "fluorouracilo": {"base": "bsa", "mg_m2": 400},
    "leucovorina": {"base": "bsa", "mg_m2": 400},
    "irinotecan": {"base": "bsa", "mg_m2": 180},
    "capecitabina": {"base": "bsa", "mg_m2": 1000},
    "bevacizumab": {"base": "peso", "mg_kg": 5},
    "cetuximab": {"base": "bsa", "mg_m2": 500},
    "panitumumab": {"base": "peso", "mg_kg": 6},
    "pembrolizumab": {"base": "fija", "mg": 200},
    "nivolumab": {"base": "peso", "mg_kg": 3},
    "ipilimumab": {"base": "peso", "mg_kg": 1},
    "encorafenib": {"base": "fija", "mg": 300},
    "regorafenib": {"base": "fija", "mg": 160},
    "trifluridina_tipiracilo": {"base": "bsa", "mg_m2": 35},
}

MONODROGAS_CATALOGO = [
    "fluorouracilo", "leucovorina", "oxaliplatino", "irinotecan",
    "capecitabina", "bevacizumab", "cetuximab", "panitumumab",
    "encorafenib", "pembrolizumab", "nivolumab", "ipilimumab",
    "regorafenib", "trifluridina_tipiracilo",
]

FARMACOS_ORALES = frozenset({
    "capecitabina", "encorafenib", "regorafenib", "trifluridina_tipiracilo",
})


def nombre_regimen(id_regimen):
    """Devuelve el nombre legible del regimen dado su ID."""
    try:
        reg = REGIMENES.get(id_regimen)
        if reg is None:
            return id_regimen
        return reg["nombre"]
    except Exception as exc:
        logger.error("Error al obtener nombre de regimen %s: %s", id_regimen, exc, exc_info=True)
        raise


def farmacos_regimen(id_regimen, base_regimen=None):
    """Devuelve la lista de farmacos del regimen dado su ID.

    Para R07/R08 (base + biologic) se expanden con los farmacos de la base
    (por defecto R01), igual que en el pipeline de entrenamiento.
    """
    try:
        reg = REGIMENES.get(id_regimen)
        if reg is None:
            return []
        farmacos = list(reg["farmacos"])
        if id_regimen in ("R07", "R08"):
            base = base_regimen or "R01"
            if base != id_regimen and base in REGIMENES:
                farmacos = list(REGIMENES[base]["farmacos"]) + farmacos
        return farmacos
    except Exception as exc:
        logger.error("Error al obtener farmacos de regimen %s: %s", id_regimen, exc, exc_info=True)
        raise


def flags_regimen(id_regimen, farmacos=None, base_regimen=None):
    """Deriva flags del regimen: n_farmacos, anti-EGFR, antiangiogenico, inmuno, dirigido."""
    try:
        if farmacos is None:
            farmacos = farmacos_regimen(id_regimen, base_regimen=base_regimen)
        farmacos_set = set(farmacos)
        return {
            "n_farmacos": len(farmacos),
            "tiene_anti_egfr": 1 if ("cetuximab" in farmacos_set or "panitumumab" in farmacos_set) else 0,
            "tiene_antiangiogenico": 1 if "bevacizumab" in farmacos_set else 0,
            "es_inmunoterapia": 1 if (
                "pembrolizumab" in farmacos_set
                or "nivolumab" in farmacos_set
                or "ipilimumab" in farmacos_set
            ) else 0,
            "es_dirigido": 1 if "encorafenib" in farmacos_set else 0,
        }
    except Exception as exc:
        logger.error("Error al derivar flags de regimen %s: %s", id_regimen, exc, exc_info=True)
        raise


def calcular_excedente_relativo(excedente_total_mg, dosis_requerida_total_mg):
    """Calcula el excedente relativo de dosis."""
    try:
        if dosis_requerida_total_mg is None or dosis_requerida_total_mg <= 0:
            return 0.0
        return float(excedente_total_mg) / float(dosis_requerida_total_mg)
    except Exception as exc:
        logger.error("Error al calcular excedente relativo: %s", exc, exc_info=True)
        raise
