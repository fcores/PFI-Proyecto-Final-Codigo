"""
Reentrenamiento del modelo GBM desde dataset_colon local.

Camino critico sin red ni catalogo Alfabeta: carga el CSV/parquet ya generado,
codifica con preparar_features_dataframe (encoding congelado) y guarda el
artefacto versionado.

Uso (desde la raiz del repo):
    python -m ml_models.reentrenar_desde_dataset
    python -m ml_models.reentrenar_desde_dataset --semilla 42
"""

import argparse
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.ml.codificacion import CATEGORIAS_MODELO, preparar_features_dataframe
from backend.ml.reglas import aplicar_reglas

logger = logging.getLogger("reentrenar_desde_dataset")

SEMILLA_DEFAULT = 42
VERSION_MODELO = "1.0.0"


def configurar_logging(script_dir):
    """Configura logging con RotatingFileHandler hacia archivo .log."""
    try:
        log_dir = script_dir / "artefactos"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "reentrenar_desde_dataset.log"
        handler = RotatingFileHandler(
            str(log_path),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        if not root.handlers:
            root.addHandler(handler)
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            root.addHandler(console)
    except Exception as exc:
        logger.error("Error al configurar logging: %s", exc, exc_info=True)
        raise


def cargar_dataset(dir_datos):
    """Carga dataset_colon.csv o, si no existe, dataset_colon.parquet."""
    try:
        csv_path = dir_datos / "dataset_colon.csv"
        parquet_path = dir_datos / "dataset_colon.parquet"
        if csv_path.exists():
            logger.info("Cargando dataset desde %s", csv_path)
            return pd.read_csv(csv_path)
        if parquet_path.exists():
            logger.info("Cargando dataset desde %s", parquet_path)
            return pd.read_parquet(parquet_path)
        raise FileNotFoundError(
            "No se encontro dataset_colon.csv ni dataset_colon.parquet en %s" % dir_datos
        )
    except Exception as exc:
        logger.error("Error al cargar dataset: %s", exc, exc_info=True)
        raise


def prediccion_capa_reglas(df):
    """Aplica aplicar_reglas fila a fila y devuelve array 1=OK / 0=rechazo."""
    try:
        pred = np.ones(len(df), dtype=int)
        for i, (_, row) in enumerate(df.iterrows()):
            motivos = aplicar_reglas(row.to_dict())
            if motivos:
                pred[i] = 0
        return pred
    except Exception as exc:
        logger.error("Error en prediccion_capa_reglas: %s", exc, exc_info=True)
        raise


def resolver_columna_grupos(dataset):
    """Obtiene la columna de grupos para StratifiedGroupKFold."""
    try:
        if "id_paciente_base" in dataset.columns:
            return dataset["id_paciente_base"].values
        if "case_submitter_id" in dataset.columns:
            return dataset["case_submitter_id"].values
        return np.arange(len(dataset))
    except Exception as exc:
        logger.error("Error al resolver columna de grupos: %s", exc, exc_info=True)
        raise


def entrenar_modelo(dataset, semilla):
    """Entrena LightGBM, calibra y calcula metricas basicas."""
    try:
        X = preparar_features_dataframe(dataset)
        y = dataset["es_valido"].astype(int).values
        groups = resolver_columna_grupos(dataset)

        pred_reglas = prediccion_capa_reglas(dataset)
        recall_reglas = recall_score(y == 0, pred_reglas == 0)

        rng = np.random.default_rng(semilla)
        sgkf = StratifiedGroupKFold(
            n_splits=5, shuffle=True, random_state=int(rng.integers(1e6))
        )

        y_proba_lgb = np.zeros(len(y), dtype=float)
        y_pred_lgb = np.zeros(len(y), dtype=int)
        n_pos = (y == 1).sum()
        n_neg = (y == 0).sum()
        scale_pos = n_neg / max(n_pos, 1)

        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "max_depth": 4,
            "num_leaves": 12,
            "min_child_samples": 15,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "scale_pos_weight": scale_pos,
            "learning_rate": 0.05,
            "verbose": -1,
            "seed": semilla,
        }

        for fold, (train_idx, val_idx) in enumerate(sgkf.split(X, y, groups)):
            X_train = X.iloc[train_idx]
            X_val = X.iloc[val_idx]
            y_train = y[train_idx]
            dtrain = lgb.Dataset(X_train, label=y_train)
            dval = lgb.Dataset(X_val, label=y[val_idx], reference=dtrain)
            fold_params = dict(params)
            fold_params["seed"] = int(rng.integers(1e6))
            model = lgb.train(
                fold_params,
                dtrain,
                num_boost_round=300,
                valid_sets=[dval],
                callbacks=[lgb.early_stopping(30, verbose=False)],
            )
            y_proba_lgb[val_idx] = model.predict(X_val)
            y_pred_lgb[val_idx] = (y_proba_lgb[val_idx] >= 0.5).astype(int)
            logger.info("Fold %d entrenado", fold + 1)

        iso_reg = IsotonicRegression(out_of_bounds="clip")
        iso_reg.fit(y_proba_lgb, y)
        y_proba_calibrada = iso_reg.predict(y_proba_lgb)

        t_bajo = float(np.percentile(y_proba_calibrada[y == 0], 70))
        t_alto = float(np.percentile(y_proba_calibrada[y == 1], 30))
        if t_bajo >= t_alto:
            t_bajo, t_alto = 0.35, 0.65

        recall_lgb = recall_score(y == 0, y_pred_lgb == 0)
        auc_roc = roc_auc_score(y, y_proba_calibrada)
        auc_pr = average_precision_score(1 - y, 1 - y_proba_calibrada)
        brier = brier_score_loss(y, y_proba_calibrada)

        # Hybrid detection: rules OR model flags as non-concordant
        pred_hibrido = np.where((pred_reglas == 0) | (y_pred_lgb == 0), 0, 1)
        recall_hibrido = recall_score(y == 0, pred_hibrido == 0)
        precision_hibrido = precision_score(y == 0, pred_hibrido == 0, zero_division=0)
        vp_hibrido = int(((y == 0) & (pred_hibrido == 0)).sum())
        fp_hibrido = int(((y == 1) & (pred_hibrido == 0)).sum())

        # Detection stats per layer
        vp_reglas = int(((y == 0) & (pred_reglas == 0)).sum())
        fp_reglas = int(((y == 1) & (pred_reglas == 0)).sum())
        precision_reglas = vp_reglas / max(vp_reglas + fp_reglas, 1)
        vp_ml = int(((y == 0) & (y_pred_lgb == 0)).sum())
        fp_ml = int(((y == 1) & (y_pred_lgb == 0)).sum())
        precision_ml = vp_ml / max(vp_ml + fp_ml, 1)

        # Recall by alcance_reglas (if column present)
        recall_por_alcance = {}
        if "alcance_reglas" in dataset.columns:
            for scope in ["dentro", "fuera"]:
                mask = dataset["alcance_reglas"].values == scope
                if mask.sum() > 0:
                    y_scope = y[mask]
                    if (y_scope == 0).sum() > 0:
                        recall_ml_scope = recall_score(
                            y_scope == 0, y_pred_lgb[mask] == 0
                        )
                        recall_reglas_scope = recall_score(
                            y_scope == 0, pred_reglas[mask] == 0
                        )
                        recall_por_alcance[scope] = {
                            "n": int(mask.sum()),
                            "recall_ml": round(float(recall_ml_scope), 4),
                            "recall_reglas": round(float(recall_reglas_scope), 4),
                        }

        # Three-state policy
        aprobados = y_proba_calibrada >= t_alto
        rechazados = y_proba_calibrada <= t_bajo
        revision = ~aprobados & ~rechazados
        n_total = len(y)
        politica_tres_estados = {
            "tasa_aprobacion_automatica": round(float(aprobados.sum() / n_total), 4),
            "tasa_derivacion_revision": round(float(revision.sum() / n_total), 4),
            "tasa_no_autorizacion": round(float(rechazados.sum() / n_total), 4),
        }

        # Recall at fixed 20% revision rate
        sorted_idx = np.argsort(y_proba_calibrada)
        n_review = int(0.20 * n_total)
        review_idx = sorted_idx[:n_review]
        recall_at_20 = float((y[review_idx] == 0).sum() / max((y == 0).sum(), 1))

        # Train final model
        dtrain_full = lgb.Dataset(X, label=y)
        model_final = lgb.train(params, dtrain_full, num_boost_round=200)

        # SHAP importance via pred_contrib
        shap_importance = {}
        try:
            contrib = model_final.predict(X, pred_contrib=True)
            feature_names = list(X.columns)
            abs_mean = np.abs(contrib[:, :-1]).mean(axis=0)
            shap_importance = {
                feature_names[i]: round(float(abs_mean[i]), 4)
                for i in range(len(feature_names))
            }
            shap_importance = dict(
                sorted(shap_importance.items(), key=lambda x: -x[1])
            )
        except Exception as e:
            logger.warning("SHAP computation failed: %s", e)

        metricas = {
            "lgbm_recall_no_concordante": round(float(recall_lgb), 4),
            "recall_por_alcance_reglas": recall_por_alcance,
            "lgbm_auc_roc": round(float(auc_roc), 4),
            "lgbm_auc_pr": round(float(auc_pr), 4),
            "lgbm_brier_score": round(float(brier), 4),
            "lgbm_recall_at_20pct_revision": round(float(recall_at_20), 4),
            "reglas_recall_no_concordante": round(float(recall_reglas), 4),
            "delta_ml_sobre_reglas": round(float(recall_lgb - recall_reglas), 4),
            "umbral_bajo": round(t_bajo, 4),
            "umbral_alto": round(t_alto, 4),
            "umbrales_por_fallback": bool(t_bajo >= t_alto),
            "deteccion_reglas": {
                "recall": round(float(recall_reglas), 4),
                "precision": round(float(precision_reglas), 4),
                "verdaderos_positivos": vp_reglas,
                "falsos_positivos": fp_reglas,
            },
            "deteccion_ml": {
                "recall": round(float(recall_lgb), 4),
                "precision": round(float(precision_ml), 4),
                "verdaderos_positivos": vp_ml,
                "falsos_positivos": fp_ml,
            },
            "deteccion_hibrido": {
                "recall": round(float(recall_hibrido), 4),
                "precision": round(float(precision_hibrido), 4),
                "verdaderos_positivos": vp_hibrido,
                "falsos_positivos": fp_hibrido,
            },
            "delta_hibrido_sobre_reglas": round(float(recall_hibrido - recall_reglas), 4),
            "politica_tres_estados": politica_tres_estados,
            "n_features": int(X.shape[1]),
            "n_filas_entrenamiento": int(len(y)),
            "shap_importance": shap_importance,
            "version_modelo": VERSION_MODELO,
            "semilla": semilla,
        }

        artefacto = {
            "model": model_final,
            "calibrador": iso_reg,
            "umbrales": {"t_bajo": t_bajo, "t_alto": t_alto},
            "features": list(X.columns),
            "categorias": CATEGORIAS_MODELO,
            "version_modelo": VERSION_MODELO,
        }
        return artefacto, metricas
    except Exception as exc:
        logger.error("Error al entrenar modelo: %s", exc, exc_info=True)
        raise


def guardar_artefactos(artefacto, metricas, dir_artefactos):
    """Persiste joblib, categorias y metricas en la carpeta de artefactos."""
    try:
        dir_artefactos.mkdir(parents=True, exist_ok=True)
        joblib.dump(artefacto, dir_artefactos / "modelo_gbm.joblib")
        with open(dir_artefactos / "categorias_modelo.json", "w", encoding="utf-8") as f:
            json.dump(CATEGORIAS_MODELO, f, indent=2, ensure_ascii=False)
        with open(dir_artefactos / "metricas_modelo.json", "w", encoding="utf-8") as f:
            json.dump(metricas, f, indent=2, ensure_ascii=False, default=str)
        logger.info("Artefactos guardados en %s", dir_artefactos)
    except Exception as exc:
        logger.error("Error al guardar artefactos: %s", exc, exc_info=True)
        raise


def main():
    """Punto de entrada: reentrena desde dataset local y guarda artefactos."""
    try:
        script_dir = Path(__file__).resolve().parent
        configurar_logging(script_dir)

        parser = argparse.ArgumentParser(
            description="Reentrenamiento GBM desde dataset_colon local"
        )
        parser.add_argument(
            "--semilla",
            type=int,
            default=SEMILLA_DEFAULT,
            help="Semilla para reproducibilidad",
        )
        args = parser.parse_args()

        dir_datos = script_dir / "datos"
        dir_artefactos = script_dir / "artefactos"

        logger.info("Inicio reentrenamiento (semilla=%s)", args.semilla)
        dataset = cargar_dataset(dir_datos)
        logger.info("Dataset cargado: %d filas", len(dataset))

        artefacto, metricas = entrenar_modelo(dataset, args.semilla)
        guardar_artefactos(artefacto, metricas, dir_artefactos)

        print("Reentrenamiento completado")
        print("  Filas: %d" % metricas["n_filas_entrenamiento"])
        print("  Recall no concordante: %.4f" % metricas["lgbm_recall_no_concordante"])
        print("  AUC-ROC: %.4f" % metricas["lgbm_auc_roc"])
        print("  Artefactos: %s" % dir_artefactos)
    except Exception as exc:
        logger.error("Error en main: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
