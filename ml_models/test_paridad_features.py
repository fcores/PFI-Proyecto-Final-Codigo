"""Test de regresion: paridad entre FeatureMapper del backend y preparar_features_dataframe.

Uso (desde la raiz del repo):
    python -m ml_models.test_paridad_features
"""
import logging
import sys
from pathlib import Path

import pandas as pd

from backend.ml.codificacion import preparar_features_dataframe
from backend.ml.feature_mapper import (
    mapear_lateralidad,
    mapear_linea,
    mapear_sexo,
    prescription_a_features,
)
from backend.ml.model_loader import cargar_modelo

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _localizacion_desde_lateralidad(lat):
    """Convierte lateralidad del dataset a etiqueta del formulario."""
    try:
        if lat == "derecho":
            return "Colon derecho"
        if lat == "izquierdo":
            return "Colon izquierdo"
        if lat == "transverso":
            return "Colon transverso"
        return "Colon derecho"
    except Exception as exc:
        logger.error("Error al mapear localizacion: %s", exc, exc_info=True)
        raise


def _sexo_formulario(sexo):
    """Convierte sexo del dataset a etiqueta del formulario."""
    try:
        if sexo == "male":
            return "Masculino"
        if sexo == "female":
            return "Femenino"
        return "Masculino"
    except Exception as exc:
        logger.error("Error al mapear sexo formulario: %s", exc, exc_info=True)
        raise


def _linea_formulario(linea):
    """Convierte linea numerica a etiqueta del formulario."""
    try:
        if int(linea) == 2:
            return "Segunda"
        return "Primera"
    except Exception as exc:
        logger.error("Error al mapear linea formulario: %s", exc, exc_info=True)
        raise


def _estadio_romano(valor):
    """Convierte estadio numerico del dataset a romano del formulario."""
    try:
        mapa = {1: "I", 2: "II", 3: "III", 4: "IV"}
        if pd.isna(valor):
            return "III"
        return mapa.get(int(valor), "III")
    except Exception as exc:
        logger.error("Error al convertir estadio: %s", exc, exc_info=True)
        raise


def _histologia_formulario(valor):
    """Convierte histologia agrupada a texto de formulario."""
    try:
        if valor == "mucinoso":
            return "Adenocarcinoma mucinoso"
        if valor == "adenocarcinoma_nos":
            return "Adenocarcinoma"
        return "Otro"
    except Exception as exc:
        logger.error("Error al convertir histologia: %s", exc, exc_info=True)
        raise


def _fila_a_prescription_like(row):
    """Arma un dict compatible con PrescriptionBase a partir de una fila del dataset."""
    try:
        return {
            "edad": row.get("edad"),
            "sexo": _sexo_formulario(row.get("sexo")),
            "peso_kg": row.get("peso_kg"),
            "talla_cm": row.get("talla_cm", 170),
            "localizacion_tumor": _localizacion_desde_lateralidad(row.get("lateralidad")),
            "tipo_histologico": _histologia_formulario(row.get("histologia")),
            "t": "T%s" % int(row.get("t")) if pd.notna(row.get("t")) else "T3",
            "n": "N%s" % int(row.get("n")) if pd.notna(row.get("n")) else "N0",
            "m": row.get("m") or "M0",
            "estadio": _estadio_romano(row.get("estadio")),
            "msi": row.get("msi") or "no_evaluado",
            "ras": row.get("ras") or "no_evaluado",
            "braf_v600e": row.get("braf_v600e") or "no_evaluado",
            "linea_tratamiento": _linea_formulario(row.get("linea_tratamiento", 1)),
            "id_regimen": row.get("id_regimen"),
        }
    except Exception as exc:
        logger.error("Error al convertir fila a prescription: %s", exc, exc_info=True)
        raise


def main():
    """Compara matrices de features del entrenamiento vs FeatureMapper."""
    try:
        root = Path(__file__).resolve().parent
        ruta_csv = root / "datos" / "dataset_colon.csv"
        if not ruta_csv.exists():
            print("FAIL: no existe %s" % ruta_csv)
            return 1

        df = pd.read_csv(ruta_csv)
        if "tipo_error" in df.columns:
            df = df[df["tipo_error"].isin(["sin_error", 0, "0"]) | (df["tipo_error"].isna())]
        if "es_valido" in df.columns:
            df = df[df["es_valido"] == 1]
        if df.empty:
            print("FAIL: no hay filas concordantes para comparar")
            return 1
        n = min(50, len(df))
        sample = df.sample(n=n, random_state=42).reset_index(drop=True)
        X_train = preparar_features_dataframe(sample)

        artefacto = cargar_modelo()
        feature_names = None
        if artefacto is not None:
            feature_names = artefacto.get("features")

        max_diff = 0.0
        mismatches = 0
        for idx, row in sample.iterrows():
            presc = _fila_a_prescription_like(row)
            superficie = row.get("superficie_corporal_m2")
            if pd.isna(superficie):
                superficie = 1.8
            excedente = row.get("excedente_relativo")
            if pd.isna(excedente):
                excedente = 0.0

            X_serve, _datos = prescription_a_features(
                presc,
                float(superficie),
                float(excedente),
                orden_features=feature_names or list(X_train.columns),
            )

            for col_i, col in enumerate(feature_names or list(X_train.columns)):
                train_val = float(X_train.loc[idx, col])
                serve_val = float(X_serve[col_i])
                diff = abs(train_val - serve_val)
                if diff > 1e-6:
                    mismatches += 1
                    if diff > max_diff:
                        max_diff = diff

        print("Filas comparadas: %d" % n)
        print("Celdas con diferencia: %d" % mismatches)
        print("Max diff: %.6f" % max_diff)

        # Sanity de mapeadores
        assert mapear_sexo("Masculino") == "male"
        assert mapear_lateralidad("Colon izquierdo") == "izquierdo"
        assert mapear_linea("Primera") == 1

        if mismatches > 0:
            print("FAIL: deriva detectada entre FeatureMapper y entrenamiento")
            return 1
        print("OK: paridad train/serve verificada")
        return 0
    except Exception as exc:
        logger.error("Error en test de paridad: %s", exc, exc_info=True)
        print("FAIL: %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
