"""Codificacion categorica congelada, features del modelo y colapsadores TNM."""
import logging
import re

logger = logging.getLogger(__name__)

FEATURES_MODELO = [
    "edad", "t", "n", "estadio", "superficie_corporal_m2", "peso_kg",
    "n_farmacos", "tiene_anti_egfr", "tiene_antiangiogenico",
    "es_inmunoterapia", "es_dirigido", "excedente_relativo",
    "linea_tratamiento",
]

FEATURES_CATEGORICAS_MODELO = [
    "sexo", "lateralidad", "histologia", "msi", "ras", "braf_v600e", "m", "id_regimen",
]

CATEGORIAS_MODELO = {
    "sexo": {"female": 0, "male": 1},
    "lateralidad": {"derecho": 0, "izquierdo": 1, "transverso": 2},
    "histologia": {"adenocarcinoma_nos": 0, "mucinoso": 1, "otros": 2},
    "msi": {"MSI-H": 0, "MSS": 1, "no_evaluado": 2},
    "ras": {"mutado": 0, "no_evaluado": 1, "wild_type": 2},
    "braf_v600e": {
        "no_evaluado": 0,
        "presente": 1,
        "wild_type": 2,
        "ausente": 2,
    },
    "m": {"M0": 0, "M1": 1, "MX": 2},
    "id_regimen": {
        "R00": 0, "R01": 1, "R02": 2, "R03": 3, "R04": 4,
        "R05": 5, "R06": 6, "R07": 7, "R08": 8, "R09": 9,
        "R10": 10, "R11": 11, "R12": 12, "R13": 13,
    },
}


def colapsar_t(valor):
    """Colapsa T1->1, T2->2, T3->3, T4/T4a/T4b->4, Tis->0."""
    try:
        if valor is None:
            return None
        v = str(valor).upper().strip()
        if "IS" in v:
            return 0
        m = re.search(r"T(\d)", v)
        return int(m.group(1)) if m else None
    except Exception as exc:
        logger.error("Error al colapsar T '%s': %s", valor, exc, exc_info=True)
        raise


def colapsar_n(valor):
    """Colapsa N0->0, N1/N1a/b/c->1, N2/N2a/b->2."""
    try:
        if valor is None:
            return None
        v = str(valor).upper().strip()
        m = re.search(r"N(\d)", v)
        return int(m.group(1)) if m else None
    except Exception as exc:
        logger.error("Error al colapsar N '%s': %s", valor, exc, exc_info=True)
        raise


def colapsar_m(valor):
    """Colapsa M0, M1, MX como tres estados."""
    try:
        if valor is None:
            return None
        v = str(valor).upper().strip()
        if "MX" in v:
            return "MX"
        m = re.search(r"M(\d)", v)
        if m:
            return "M1" if int(m.group(1)) >= 1 else "M0"
        return None
    except Exception as exc:
        logger.error("Error al colapsar M '%s': %s", valor, exc, exc_info=True)
        raise


def colapsar_estadio(valor):
    """Colapsa Stage I/IA->1, II/IIA/IIB/IIC->2, III/IIIA/B/C->3, IV/IVA/IVB->4."""
    try:
        if valor is None:
            return None
        v = str(valor).upper().replace("STAGE", "").strip()
        if v.startswith("IV"):
            return 4
        if v.startswith("III"):
            return 3
        if v.startswith("II"):
            return 2
        if v.startswith("I"):
            return 1
        return None
    except Exception as exc:
        logger.error("Error al colapsar estadio '%s': %s", valor, exc, exc_info=True)
        raise


def histologia_agrupada(valor):
    """Agrupa histologia en adenocarcinoma_nos, mucinoso u otros."""
    try:
        if valor is None:
            return None
        v = str(valor).lower()
        if "mucinous" in v or "mucinoso" in v:
            return "mucinoso"
        if "adenocarcinoma" in v:
            return "adenocarcinoma_nos"
        return "otros"
    except Exception as exc:
        logger.error("Error al agrupar histologia '%s': %s", valor, exc, exc_info=True)
        raise


def normalizar_valor_categorico(columna, valor):
    """Normaliza alias de categorias (ej. BRAF ausente -> wild_type)."""
    try:
        if valor is None:
            return None
        if isinstance(valor, float):
            import math
            if math.isnan(valor):
                return None
        if columna == "braf_v600e" and valor == "ausente":
            return "wild_type"
        return valor
    except Exception as exc:
        logger.error("Error al normalizar %s='%s': %s", columna, valor, exc, exc_info=True)
        raise


def codificar_categorica(columna, valor):
    """Codifica un valor categorico usando el mapeo congelado de CATEGORIAS_MODELO."""
    try:
        mapeo = CATEGORIAS_MODELO.get(columna)
        if mapeo is None:
            return -1
        valor_norm = normalizar_valor_categorico(columna, valor)
        if valor_norm is None:
            return -1
        return mapeo.get(valor_norm, -1)
    except Exception as exc:
        logger.error("Error al codificar %s='%s': %s", columna, valor, exc, exc_info=True)
        raise


def preparar_features(datos):
    """Prepara el diccionario de features para el modelo a partir de un dict de datos crudos.

    Recibe un diccionario con las claves del modelo y devuelve un diccionario
    con las 21 features numericas listas para predecir, usando la codificacion
    congelada de CATEGORIAS_MODELO.
    """
    try:
        features = {}
        for col in FEATURES_MODELO:
            val = datos.get(col)
            if val is None:
                features[col] = -1
            else:
                try:
                    features[col] = float(val)
                except (ValueError, TypeError):
                    features[col] = -1

        for col in FEATURES_CATEGORICAS_MODELO:
            val = datos.get(col)
            if val is None:
                features[col] = -1
            else:
                features[col] = codificar_categorica(col, val)

        return features
    except Exception as exc:
        logger.error("Error al preparar features: %s", exc, exc_info=True)
        raise


def preparar_features_dataframe(df):
    """Prepara la matriz de features para entrenamiento a partir de un DataFrame.

    Usa la misma codificacion congelada de CATEGORIAS_MODELO que preparar_features,
    garantizando paridad train/serve.
    """
    try:
        import pandas as pd

        X = pd.DataFrame(index=df.index)

        for col in FEATURES_MODELO:
            if col in df.columns:
                X[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                X[col] = -1

        for col in FEATURES_CATEGORICAS_MODELO:
            if col in df.columns:
                valores = []
                for val in df[col].tolist():
                    valores.append(codificar_categorica(col, val))
                X[col] = valores
            else:
                X[col] = -1

        X = X.fillna(-1)
        return X
    except Exception as exc:
        logger.error("Error al preparar features dataframe: %s", exc, exc_info=True)
        raise
