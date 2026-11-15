"""
entrenar_modelo.py — Pipeline completo para el PFI UADE
========================================================
Cancer de colon: extraccion TCGA-COAD + cBioPortal, perfilado de calidad,
EDA, construccion del dataset hibrido, entrenamiento gradient boosting.

La logica compartida (regimenes, codificacion, dosis, guias, reglas) vive en
backend.ml y se importa desde aqui para mantener paridad train/serve.

Uso (desde la raiz del repo):
    python -m ml_models.entrenar_modelo
    python -m ml_models.entrenar_modelo --sin-red
    python -m ml_models.entrenar_modelo --semilla 42
    python -m ml_models.entrenar_modelo --salida ./mi_salida
"""

import argparse
import json
import logging
import math
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy import stats
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.tree import DecisionTreeClassifier

import lightgbm as lgb

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.ml.regimenes import REGIMENES, DOSIS_REFERENCIA, MONODROGAS_CATALOGO
from backend.ml.codificacion import (
    FEATURES_MODELO,
    FEATURES_CATEGORICAS_MODELO,
    CATEGORIAS_MODELO,
    colapsar_t,
    colapsar_n,
    colapsar_m,
    colapsar_estadio,
    histologia_agrupada,
    preparar_features_dataframe,
)
from backend.ml.dosis import calcular_dosis_mg, resolver_presentaciones
from backend.ml.guias import regimen_por_guias
from backend.ml.reglas import aplicar_reglas

warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACION
# ============================================================================

PROP_CONCORDANTES = 0.55
ALCANCE_LINEAS = (1, 2)
SINTETIZAR_ECOG = False
FRAC_AMBIGUOS = 0.18
FRAC_ERRORES_FUERA_DE_REGLAS = 0.35
SEMILLA = 42

CENTINELAS_NULOS = [
    "[Not Available]", "[Not Applicable]", "[Unknown]",
    "[Discrepancy]", "[Not Evaluated]", "[Pending]",
    "[Redacted]", "not reported", "unknown", "",
]

HF_BASE = "https://datasets-server.huggingface.co/rows"
HF_DATASET = "gabrielaltay/tcga-tabular-open"
CBIO_BASE = "https://www.cbioportal.org/api"
CBIO_STUDY = "coadread_tcga_pan_can_atlas_2018"

SUBSITIO_A_LATERALIDAD = {
    "Cecum": "derecho", "Ascending Colon": "derecho",
    "Hepatic Flexure": "derecho", "Transverse Colon": "transverso",
    "Splenic Flexure": "izquierdo", "Descending Colon": "izquierdo",
    "Sigmoid Colon": "izquierdo", "Rectosigmoid Junction": "izquierdo",
    "Ascending colon": "derecho", "Descending colon": "izquierdo",
    "Sigmoid colon": "izquierdo", "Transverse colon": "transverso",
    "Hepatic flexure": "derecho", "Splenic flexure": "izquierdo",
    "Rectosigmoid junction": "izquierdo",
    "Colon, NOS": "transverso",
    "Right Colon": "derecho", "Left Colon": "izquierdo",
}


# ============================================================================
# SECCION 1: EXTRACCION CON CACHE LOCAL
# ============================================================================

def _hf_descargar_tabla(config: str, cache_dir: Path, sin_red: bool) -> pd.DataFrame:
    """Descarga una tabla TCGA_COAD_* desde HF datasets-server con paginado."""
    cache_path = cache_dir / f"{config}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    if sin_red:
        raise FileNotFoundError(f"Cache no encontrado para {config} y --sin-red activo")

    rows = []
    offset = 0
    page_size = 100
    while True:
        url = f"{HF_BASE}?dataset={HF_DATASET}&config={config}&split=train&offset={offset}&length={page_size}"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        batch = [r["row"] for r in data.get("rows", [])]
        if not batch:
            break
        rows.extend(batch)
        offset += page_size
        if offset >= data.get("num_rows_total", 0):
            break
        time.sleep(0.3)

    df = pd.DataFrame(rows)
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    print(f"  [HF] {config}: {len(df)} filas descargadas y cacheadas")
    return df


def _cbio_get(endpoint: str, params: dict = None) -> Any:
    """GET a la API publica de cBioPortal."""
    headers = {"Accept": "application/json", "User-Agent": "PFI-UADE/1.0"}
    resp = requests.get(f"{CBIO_BASE}{endpoint}", params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _cbio_post(endpoint: str, body: dict) -> Any:
    """POST a la API publica de cBioPortal."""
    headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "PFI-UADE/1.0"}
    resp = requests.post(f"{CBIO_BASE}{endpoint}", json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _cbio_descargar_clinicos(cache_dir: Path, sin_red: bool) -> pd.DataFrame:
    """Descarga datos clinicos de cBioPortal (MANTIS, MSIsensor)."""
    cache_path = cache_dir / "cbio_clinical.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    if sin_red:
        raise FileNotFoundError("Cache cbio_clinical no encontrado y --sin-red activo")

    data = _cbio_get(f"/studies/{CBIO_STUDY}/clinical-data", {"clinicalDataType": "SAMPLE", "pageSize": 10000})
    df = pd.DataFrame(data)
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    print(f"  [cBio] clinical-data: {len(df)} registros")
    return df


def _cbio_descargar_mutaciones(cache_dir: Path, sin_red: bool) -> pd.DataFrame:
    """Descarga mutaciones de KRAS, NRAS, BRAF."""
    cache_path = cache_dir / "cbio_mutations.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    if sin_red:
        raise FileNotFoundError("Cache cbio_mutations no encontrado y --sin-red activo")

    mol_profile = f"{CBIO_STUDY}_mutations"
    entrez_ids = [3845, 4893, 673]  # KRAS, NRAS, BRAF

    all_mutations = []
    for gene_id in entrez_ids:
        try:
            body = {
                "sampleListId": f"{CBIO_STUDY}_all",
                "entrezGeneIds": [gene_id],
            }
            muts = _cbio_post(f"/molecular-profiles/{mol_profile}/mutations/fetch", body)
            all_mutations.extend(muts)
            time.sleep(0.5)
        except Exception as e:
            print(f"  [cBio] Warning: no se pudieron obtener mutaciones para entrez {gene_id}: {e}")

    df = pd.DataFrame(all_mutations) if all_mutations else pd.DataFrame()
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    print(f"  [cBio] mutaciones: {len(df)} filas")
    return df


def extraer_datos(cache_dir: Path, sin_red: bool) -> Dict[str, pd.DataFrame]:
    """Extrae todas las tablas necesarias."""
    print("\n=== SECCION 1: EXTRACCION ===")
    tablas = {}

    configs = [
        "TCGA_COAD_cases",
        "TCGA_COAD_clinical_supplement_patient",
        "TCGA_COAD_clinical_supplement_drug",
        "TCGA_COAD_clinical_supplement_follow_up",
    ]
    for cfg in configs:
        tablas[cfg] = _hf_descargar_tabla(cfg, cache_dir, sin_red)

    tablas["cbio_clinical"] = _cbio_descargar_clinicos(cache_dir, sin_red)
    tablas["cbio_mutations"] = _cbio_descargar_mutaciones(cache_dir, sin_red)

    return tablas


# ============================================================================
# SECCION 2: NORMALIZACION DE CENTINELAS
# ============================================================================

def normalizar_centinelas(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Reemplaza centinelas de texto por NaN, antes de cualquier casteo."""
    print("\n=== SECCION 2: NORMALIZACION DE CENTINELAS ===")
    resultado = {}
    for nombre, df in tablas.items():
        df_copy = df.copy()
        for col in df_copy.select_dtypes(include=["object"]).columns:
            mask = df_copy[col].isin(CENTINELAS_NULOS) | df_copy[col].str.strip().eq("")
            n_replaced = mask.sum()
            if n_replaced > 0:
                df_copy.loc[mask, col] = np.nan
        resultado[nombre] = df_copy
    print("  Centinelas normalizados en todas las tablas")
    return resultado


# ============================================================================
# SECCION 3: PERFILADO DE CALIDAD
# ============================================================================

def perfilar_calidad(tablas: Dict[str, pd.DataFrame], dir_salida: Path) -> Dict:
    """Reproduce las cifras del informe de calidad."""
    print("\n=== SECCION 3: PERFILADO DE CALIDAD ===")
    metricas = {}

    cases = tablas["TCGA_COAD_cases"]
    cs_patient = tablas["TCGA_COAD_clinical_supplement_patient"]

    metricas["n_cases"] = len(cases)
    metricas["n_cs_patient"] = len(cs_patient)

    # Missingness real vs aparente
    for nombre_tabla in ["TCGA_COAD_clinical_supplement_patient", "TCGA_COAD_clinical_supplement_drug"]:
        df = tablas[nombre_tabla]
        total_celdas = df.size
        nulos_aparentes = df.isnull().sum().sum()
        nulos_reales = df.isnull().sum().sum()  # ya normalizado
        metricas[f"{nombre_tabla}_celdas"] = int(total_celdas)
        metricas[f"{nombre_tabla}_pct_nulos"] = round(float(nulos_reales / total_celdas * 100), 1) if total_celdas > 0 else 0

    # Embudo del esqueleto
    embudo = []
    n = len(cases)
    embudo.append({"paso": "TCGA-COAD universo", "n": n, "pct": 100.0})

    # Extraer case_submitter_id
    if "case_submitter_id" in cases.columns:
        ids_coad = set(cases["case_submitter_id"].dropna().tolist())
    else:
        ids_coad = set()

    metricas["ids_coad_count"] = len(ids_coad)
    metricas["embudo"] = embudo

    # Guardar
    dir_salida.mkdir(parents=True, exist_ok=True)
    with open(dir_salida / "metricas_calidad_tcga.json", "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False, default=str)

    print(f"  Metricas guardadas: {len(metricas)} claves")
    return metricas


# ============================================================================
# SECCION 4: EDA
# ============================================================================

def _cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Calcula V de Cramer entre dos categoricas."""
    confusion_matrix = pd.crosstab(x, y)
    chi2 = stats.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    min_dim = min(confusion_matrix.shape) - 1
    if min_dim == 0 or n == 0:
        return 0.0
    return float(np.sqrt(chi2 / (n * min_dim)))


def ejecutar_eda(df: pd.DataFrame, etiqueta: str, dir_figuras: Path, dir_salida: Path) -> Dict:
    """EDA reutilizable: univariado, bivariado, celdas de decision."""
    print(f"\n  --- EDA: {etiqueta} ({len(df)} filas, {len(df.columns)} cols) ---")
    dir_figuras.mkdir(parents=True, exist_ok=True)
    resultados = {"etiqueta": etiqueta, "n_filas": len(df), "n_cols": len(df.columns)}

    # Univariado numericas
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        desc = df[num_cols].describe().T
        desc["skew"] = df[num_cols].skew()
        desc["kurtosis"] = df[num_cols].kurtosis()
        desc["missing"] = df[num_cols].isnull().sum()
        resultados["descriptivo_numerico"] = desc.to_dict()

        # Histogramas
        n_plots = min(len(num_cols), 12)
        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        axes = axes.flatten()
        for i, col in enumerate(num_cols[:n_plots]):
            ax = axes[i]
            df[col].dropna().hist(ax=ax, bins=30, edgecolor="black", alpha=0.7)
            ax.set_title(col, fontsize=9)
        for i in range(n_plots, len(axes)):
            axes[i].set_visible(False)
        plt.suptitle(f"Histogramas - {etiqueta}", fontsize=12)
        plt.tight_layout()
        plt.savefig(dir_figuras / f"histogramas_{etiqueta}.png", dpi=100)
        plt.close()

    # Univariado categoricas
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_stats = {}
    for col in cat_cols:
        try:
            col_clean = df[col].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)
            vc = col_clean.value_counts()
            cat_stats[col] = {
                "cardinalidad": int(vc.shape[0]),
                "top_5": {str(k): int(v) for k, v in vc.head(5).items()},
                "missing": int(df[col].isnull().sum()),
            }
        except Exception:
            cat_stats[col] = {"cardinalidad": 0, "top_5": {}, "missing": int(df[col].isnull().sum())}
    resultados["categoricas"] = cat_stats

    # Barras de categoricas principales (skip cols with unhashable types)
    plottable_cats = []
    for col in cat_cols:
        try:
            df[col].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x).value_counts()
            plottable_cats.append(col)
        except Exception:
            pass

    if plottable_cats:
        n_bar = min(len(plottable_cats), 8)
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        axes = axes.flatten()
        for i, col in enumerate(plottable_cats[:n_bar]):
            ax = axes[i]
            df[col].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x).value_counts().head(8).plot.barh(ax=ax)
            ax.set_title(col, fontsize=9)
        for i in range(n_bar, len(axes)):
            axes[i].set_visible(False)
        plt.suptitle(f"Categoricas - {etiqueta}", fontsize=12)
        plt.tight_layout()
        plt.savefig(dir_figuras / f"barras_{etiqueta}.png", dpi=100)
        plt.close()

    # Correlacion de Spearman (numericas + ordinales)
    if len(num_cols) >= 2:
        corr = df[num_cols].corr(method="spearman")
        resultados["correlacion_spearman"] = corr.to_dict()
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(corr.columns, fontsize=7)
        plt.colorbar(im, ax=ax)
        plt.title(f"Spearman - {etiqueta}")
        plt.tight_layout()
        plt.savefig(dir_figuras / f"correlacion_{etiqueta}.png", dpi=100)
        plt.close()

    # Celdas de decision (si hay estadio y lateralidad)
    if "estadio" in df.columns and "lateralidad" in df.columns:
        cross = pd.crosstab(df["estadio"], df["lateralidad"], margins=True)
        resultados["celdas_estadio_lateralidad"] = cross.to_dict()

    # Para dataset generado: balance de clases
    if "es_valido" in df.columns:
        resultados["balance_es_valido"] = df["es_valido"].value_counts().to_dict()
    if "tipo_error" in df.columns:
        resultados["distribucion_tipo_error"] = df["tipo_error"].value_counts().to_dict()
        fig, ax = plt.subplots(figsize=(10, 5))
        df["tipo_error"].value_counts().plot.bar(ax=ax, edgecolor="black")
        ax.set_title(f"Tipo de error - {etiqueta}")
        plt.tight_layout()
        plt.savefig(dir_figuras / f"tipo_error_{etiqueta}.png", dpi=100)
        plt.close()
    if "id_regimen" in df.columns:
        resultados["distribucion_regimen"] = df["id_regimen"].value_counts().to_dict()

    # Guardar JSON
    json_path = dir_salida / f"eda_{etiqueta}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)

    print(f"  EDA {etiqueta} completado -> {json_path.name}")
    return resultados


# ============================================================================
# SECCION 5: BLOQUE A — ESQUELETO REAL
# ============================================================================

def _extraer_diagnostico_primario(diag_list) -> Optional[Dict]:
    """Del JSON anidado de diagnoses, extrae el primario."""
    if not isinstance(diag_list, list) or len(diag_list) == 0:
        return None
    for d in diag_list:
        if isinstance(d, dict):
            if d.get("classification_of_tumor") == "primary" or d.get("diagnosis_is_primary_disease") == "Yes":
                return d
    return diag_list[0] if isinstance(diag_list[0], dict) else None


def construir_esqueleto(tablas: Dict[str, pd.DataFrame], rng: np.random.Generator) -> pd.DataFrame:
    """Construye el bloque A: esqueleto real de ~361 pacientes."""
    print("\n=== SECCION 5: ESQUELETO REAL ===")

    cases = tablas["TCGA_COAD_cases"]
    cs_patient = tablas["TCGA_COAD_clinical_supplement_patient"]
    cbio_clin = tablas["cbio_clinical"]
    cbio_mut = tablas["cbio_mutations"]

    # Extraer datos de cases (columnas con objetos anidados)
    registros = []
    for _, row in cases.iterrows():
        rec = {"case_submitter_id": row.get("case_submitter_id")}

        # Demograficos
        demo = row.get("demographic")
        if isinstance(demo, dict):
            rec["edad"] = demo.get("age_at_index")
            rec["sexo"] = demo.get("sex_at_birth", demo.get("gender"))
        elif isinstance(demo, str):
            try:
                demo = json.loads(demo)
                rec["edad"] = demo.get("age_at_index")
                rec["sexo"] = demo.get("sex_at_birth", demo.get("gender"))
            except (json.JSONDecodeError, TypeError):
                pass

        # Diagnostico primario (puede ser numpy array o list)
        diag_list = row.get("diagnoses")
        if hasattr(diag_list, "tolist"):
            diag_list = diag_list.tolist()
        elif isinstance(diag_list, str):
            try:
                diag_list = json.loads(diag_list)
            except (json.JSONDecodeError, TypeError):
                diag_list = None

        diag = _extraer_diagnostico_primario(diag_list)
        if diag:
            rec["t_raw"] = diag.get("ajcc_pathologic_t")
            rec["n_raw"] = diag.get("ajcc_pathologic_n")
            rec["m_raw"] = diag.get("ajcc_pathologic_m")
            rec["estadio_raw"] = diag.get("ajcc_pathologic_stage")
            rec["histologia_raw"] = diag.get("primary_diagnosis")
            rec["cie10_raw"] = diag.get("icd_10_code")
            rec["subsitio_raw"] = diag.get("site_of_resection_or_biopsy", diag.get("tissue_or_organ_of_origin"))

        registros.append(rec)

    df = pd.DataFrame(registros)
    ids_coad = set(df["case_submitter_id"].dropna().tolist())
    print(f"  Cases extraidos: {len(df)}")

    # Merge con cs_patient para subsitio anatomico y antropometria
    cs_p = cs_patient.copy()
    merge_key = None
    if "case_submitter_id" in cs_p.columns:
        merge_key = "case_submitter_id"
    elif "bcr_patient_barcode" in cs_p.columns:
        cs_p = cs_p.rename(columns={"bcr_patient_barcode": "case_submitter_id"})
        merge_key = "case_submitter_id"

    if merge_key:
        cs_p = cs_p.loc[:, ~cs_p.columns.duplicated()]
        cols_patient = [merge_key]
        for c in ["anatomic_neoplasm_subdivision", "weight_kg_at_diagnosis",
                  "height_cm_at_diagnosis", "microsatellite_instability",
                  "lymphovascular_invasion_indicator", "perineural_invasion",
                  "lymph_nodes_examined_count", "gender",
                  "ajcc_tumor_pathologic_pt", "ajcc_nodes_pathologic_pn",
                  "ajcc_metastasis_pathologic_pm", "ajcc_pathologic_tumor_stage"]:
            if c in cs_p.columns:
                cols_patient.append(c)

        if len(cols_patient) > 1:
            df = df.merge(cs_p[cols_patient].drop_duplicates(subset=[merge_key]), on=merge_key, how="left")

    # Lateralidad (3 estados): priorizar anatomic_neoplasm_subdivision, luego subsitio del diagnostico
    if "anatomic_neoplasm_subdivision" in df.columns:
        df["lateralidad"] = df["anatomic_neoplasm_subdivision"].map(SUBSITIO_A_LATERALIDAD)
    else:
        df["lateralidad"] = None

    if "subsitio_raw" in df.columns:
        mask_sin_lat = df["lateralidad"].isna()
        df.loc[mask_sin_lat, "lateralidad"] = df.loc[mask_sin_lat, "subsitio_raw"].map(SUBSITIO_A_LATERALIDAD)

    # Normalize sexo to lowercase (HF uses "male"/"female", cs_patient uses "MALE"/"FEMALE")
    if "sexo" in df.columns:
        df["sexo"] = df["sexo"].astype(str).str.lower().replace("nan", np.nan)
    if "gender" in df.columns and "sexo" in df.columns:
        mask = df["sexo"].isna()
        df.loc[mask, "sexo"] = df.loc[mask, "gender"].astype(str).str.lower().replace("nan", np.nan)

    # Fallback TNM from cs_patient
    for src, dst in [("ajcc_tumor_pathologic_pt", "t_raw"), ("ajcc_nodes_pathologic_pn", "n_raw"),
                     ("ajcc_metastasis_pathologic_pm", "m_raw"), ("ajcc_pathologic_tumor_stage", "estadio_raw")]:
        if src in df.columns and dst in df.columns:
            mask = df[dst].isna()
            df.loc[mask, dst] = df.loc[mask, src]
        elif src in df.columns and dst not in df.columns:
            df[dst] = df[src]

    # Ensure raw columns exist
    for col in ["t_raw", "n_raw", "m_raw", "estadio_raw", "histologia_raw"]:
        if col not in df.columns:
            df[col] = None

    # Colapsar TNM y estadio
    df["t"] = df["t_raw"].apply(colapsar_t)
    df["n"] = df["n_raw"].apply(colapsar_n)
    df["m"] = df["m_raw"].apply(colapsar_m)
    df["estadio"] = df["estadio_raw"].apply(colapsar_estadio)
    df["histologia"] = df["histologia_raw"].apply(histologia_agrupada)

    # MSI desde cBioPortal (filtrar a COAD)
    if not cbio_clin.empty and "patientId" in cbio_clin.columns:
        cbio_coad = cbio_clin[cbio_clin["patientId"].isin(ids_coad)]
        mantis = cbio_coad[cbio_coad["clinicalAttributeId"] == "MSI_SCORE_MANTIS"][["patientId", "value"]].copy()
        mantis = mantis.rename(columns={"value": "mantis_score"})
        mantis["mantis_score"] = pd.to_numeric(mantis["mantis_score"], errors="coerce")

        msisensor = cbio_coad[cbio_coad["clinicalAttributeId"] == "MSI_SENSOR_SCORE"][["patientId", "value"]].copy()
        msisensor = msisensor.rename(columns={"value": "msisensor_score"})
        msisensor["msisensor_score"] = pd.to_numeric(msisensor["msisensor_score"], errors="coerce")

        df = df.merge(mantis.drop_duplicates("patientId"), left_on="case_submitter_id", right_on="patientId", how="left")
        df = df.merge(msisensor.drop_duplicates("patientId"), left_on="case_submitter_id", right_on="patientId", how="left", suffixes=("", "_s"))
        df.drop(columns=[c for c in df.columns if c.startswith("patientId")], inplace=True, errors="ignore")

    # MSI: union priorizada
    def _determinar_msi(row):
        # Biotab BCR
        if pd.notna(row.get("microsatellite_instability")):
            v = str(row["microsatellite_instability"]).upper()
            if "MSI-H" in v or "HIGH" in v:
                return "MSI-H"
            if "MSS" in v or "STABLE" in v or "MSI-L" in v:
                return "MSS"
        # MANTIS > 0.4
        if pd.notna(row.get("mantis_score")):
            return "MSI-H" if row["mantis_score"] > 0.4 else "MSS"
        # MSIsensor >= 10
        if pd.notna(row.get("msisensor_score")):
            return "MSI-H" if row["msisensor_score"] >= 10 else "MSS"
        return None

    df["msi"] = df.apply(_determinar_msi, axis=1)

    # RAS y BRAF desde cBioPortal mutaciones (filtrar a COAD)
    df["ras"] = "no_evaluado"
    df["braf_v600e"] = "no_evaluado"

    if not cbio_mut.empty:
        cbio_mut_coad = cbio_mut[cbio_mut["patientId"].isin(ids_coad)] if "patientId" in cbio_mut.columns else cbio_mut

        # Pacientes secuenciados (tienen al menos una entrada)
        secuenciados = set()
        if "patientId" in cbio_mut_coad.columns:
            secuenciados = set(cbio_mut_coad["patientId"].unique())
        elif "sampleId" in cbio_mut_coad.columns:
            secuenciados = set(s[:12] for s in cbio_mut_coad["sampleId"].unique())

        # Marcar wt a los secuenciados sin mutacion detectada
        for pid in secuenciados:
            mask = df["case_submitter_id"] == pid
            if mask.any():
                df.loc[mask, "ras"] = "wild_type"
                df.loc[mask, "braf_v600e"] = "ausente"

        # KRAS/NRAS mutaciones
        gene_col = "hugoGeneSymbol" if "hugoGeneSymbol" in cbio_mut_coad.columns else "gene"
        if gene_col in cbio_mut_coad.columns:
            kras_nras = cbio_mut_coad[cbio_mut_coad[gene_col].isin(["KRAS", "NRAS"])]
            pid_col = "patientId" if "patientId" in kras_nras.columns else "sampleId"
            for pid in kras_nras[pid_col].unique():
                real_pid = pid[:12] if pid_col == "sampleId" else pid
                mask = df["case_submitter_id"] == real_pid
                df.loc[mask, "ras"] = "mutado"

            # BRAF V600E
            braf = cbio_mut_coad[cbio_mut_coad[gene_col] == "BRAF"]
            if "proteinChange" in braf.columns:
                braf_v600e = braf[braf["proteinChange"].str.contains("V600E", na=False)]
            elif "aminoAcidChange" in braf.columns:
                braf_v600e = braf[braf["aminoAcidChange"].str.contains("V600E", na=False)]
            else:
                braf_v600e = pd.DataFrame()

            if not braf_v600e.empty:
                for pid in braf_v600e[pid_col].unique():
                    real_pid = pid[:12] if pid_col == "sampleId" else pid
                    mask = df["case_submitter_id"] == real_pid
                    df.loc[mask, "braf_v600e"] = "presente"

    # Antropometria
    if "weight_kg_at_diagnosis" in df.columns:
        df["peso_kg"] = pd.to_numeric(df["weight_kg_at_diagnosis"], errors="coerce")
    else:
        df["peso_kg"] = np.nan
    if "height_cm_at_diagnosis" in df.columns:
        df["talla_cm"] = pd.to_numeric(df["height_cm_at_diagnosis"], errors="coerce")
    else:
        df["talla_cm"] = np.nan

    # Corregir outliers imposibles
    df.loc[df["talla_cm"] < 140, "talla_cm"] = np.nan
    df.loc[df["peso_kg"] < 30, "peso_kg"] = np.nan

    # Sintetizar faltantes
    df["origen_peso"] = np.where(df["peso_kg"].notna(), "real", "generado")
    df["origen_talla"] = np.where(df["talla_cm"].notna(), "real", "generado")

    mask_peso_na = df["peso_kg"].isna()
    mask_talla_na = df["talla_cm"].isna()

    n_peso_gen = mask_peso_na.sum()
    n_talla_gen = mask_talla_na.sum()

    if n_peso_gen > 0:
        sexo_num = df.loc[mask_peso_na, "sexo"].map({"male": 1, "female": 0}).fillna(0.5)
        media_peso = 82 * sexo_num + 68 * (1 - sexo_num)
        df.loc[mask_peso_na, "peso_kg"] = rng.normal(media_peso, 12).clip(40, 140)

    if n_talla_gen > 0:
        sexo_num = df.loc[mask_talla_na, "sexo"].map({"male": 1, "female": 0}).fillna(0.5)
        media_talla = 175 * sexo_num + 162 * (1 - sexo_num)
        df.loc[mask_talla_na, "talla_cm"] = rng.normal(media_talla, 7).clip(145, 200)

    # BSA Mosteller
    df["superficie_corporal_m2"] = np.sqrt(df["talla_cm"] * df["peso_kg"] / 3600)

    # Ganglios
    if "lymph_nodes_examined_count" in df.columns:
        df["ganglios_examinados"] = pd.to_numeric(df["lymph_nodes_examined_count"], errors="coerce")
    else:
        df["ganglios_examinados"] = np.nan

    # LVI y PNI
    if "lymphovascular_invasion_indicator" in df.columns:
        df["lvi"] = df["lymphovascular_invasion_indicator"].map({"YES": 1, "NO": 0, "Present": 1, "Absent": 0})
    else:
        df["lvi"] = np.nan

    if "perineural_invasion" in df.columns:
        df["pni"] = df["perineural_invasion"].map({"YES": 1, "NO": 0, "Present": 1, "Absent": 0})
    else:
        df["pni"] = np.nan

    # Filtrar esqueleto: requiere edad, estadio, lateralidad minimo (no exigir molecular)
    df["id_paciente_base"] = df["case_submitter_id"]
    df["origen_paciente"] = "real"

    cols_requeridas = ["edad", "t", "n", "estadio", "lateralidad"]
    esqueleto = df.dropna(subset=[c for c in cols_requeridas if c in df.columns])

    print(f"  Esqueleto real: {len(esqueleto)} pacientes (de {len(df)} con datos)")

    # Seleccionar columnas finales
    cols_esqueleto = [
        "id_paciente_base", "origen_paciente", "edad", "sexo", "peso_kg", "talla_cm",
        "superficie_corporal_m2", "lateralidad", "histologia", "t", "n", "m", "estadio",
        "msi", "ras", "braf_v600e", "ganglios_examinados", "lvi", "pni",
        "origen_peso", "origen_talla",
    ]
    cols_esqueleto = [c for c in cols_esqueleto if c in esqueleto.columns]
    return esqueleto[cols_esqueleto].reset_index(drop=True)


# ============================================================================
# SECCION 6-7: RE-ESTADIFICACION Y SUBCONJUNTO AMBIGUO
# ============================================================================

def reestadificar_y_ambiguos(esqueleto: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Re-estadifica perfiles para celdas metastasicas criticas."""
    print("\n=== SECCION 6-7: RE-ESTADIFICACION Y AMBIGUOS ===")

    pool_base = esqueleto[esqueleto["estadio"].isin([2, 3])].copy()
    nuevos = []

    objetivos = [
        {"filtro": {"msi": "MSI-H"}, "target_n": 28, "nombre": "MSI-H IV"},
        {"filtro": {"braf_v600e": "presente"}, "target_n": 20, "nombre": "BRAF V600E IV"},
        {"filtro": {"ras": "wild_type", "lateralidad": "derecho"}, "target_n": 18, "nombre": "RAS wt derecho IV"},
        {"filtro": {"lateralidad": "transverso"}, "target_n": 14, "nombre": "Transverso IV"},
        {"filtro": {"ras": "wild_type", "lateralidad": "izquierdo"}, "target_n": 12, "nombre": "RAS wt izq IV refuerzo"},
    ]

    existentes_iv = esqueleto[esqueleto["estadio"] == 4]

    for obj in objetivos:
        mask = pd.Series(True, index=pool_base.index)
        for col, val in obj["filtro"].items():
            mask &= pool_base[col] == val

        candidatos = pool_base[mask]
        ya_en_iv = existentes_iv.copy()
        for col, val in obj["filtro"].items():
            ya_en_iv = ya_en_iv[ya_en_iv[col] == val]

        n_faltan = max(0, obj["target_n"] - len(ya_en_iv))
        n_gen = min(n_faltan, len(candidatos))

        if n_gen > 0:
            muestra = candidatos.sample(n=n_gen, replace=len(candidatos) < n_gen, random_state=int(rng.integers(1e6)))
            muestra = muestra.copy()
            muestra["estadio"] = 4
            muestra["m"] = "M1"
            muestra["origen_paciente"] = "re-estadificado"
            muestra["id_paciente_base"] = [f"RE_{i:04d}" for i in range(len(nuevos), len(nuevos) + n_gen)]
            nuevos.append(muestra)
            print(f"  {obj['nombre']}: +{n_gen} re-estadificados")

    if nuevos:
        df_nuevos = pd.concat(nuevos, ignore_index=True)
        resultado = pd.concat([esqueleto, df_nuevos], ignore_index=True)
    else:
        resultado = esqueleto.copy()

    # Marcar subconjunto ambiguo
    resultado["es_ambiguo"] = False
    mask_ambiguo = (
        (resultado["msi"].isna()) |
        (resultado["m"] == "MX") |
        (resultado["lateralidad"] == "transverso") |
        (resultado["ras"] == "no_evaluado") |
        (resultado["braf_v600e"] == "no_evaluado") |
        ((resultado["estadio"] == 2) & (resultado["t"] == 4)) |
        (resultado["superficie_corporal_m2"] < 1.4) |
        (resultado["superficie_corporal_m2"] > 2.3)
    )
    resultado.loc[mask_ambiguo, "es_ambiguo"] = True

    n_ambiguos = resultado["es_ambiguo"].sum()
    pct = n_ambiguos / len(resultado) * 100
    print(f"  Total esqueleto expandido: {len(resultado)} pacientes")
    print(f"  Ambiguos: {n_ambiguos} ({pct:.1f}%)")

    return resultado


# ============================================================================
# SECCION 8-9: CATALOGO ALFABETA Y PRESCRIPCION (guias/dosis en backend.ml)
# ============================================================================

def cargar_catalogo_alfabeta(ruta_xlsx: Path) -> pd.DataFrame:
    """Carga y normaliza el catalogo de medicamentos."""
    df = pd.read_excel(ruta_xlsx, sheet_name=0)
    df.columns = [c.strip() for c in df.columns]

    # Normalizar potencia a mg
    df["potencia_mg"] = pd.to_numeric(
        df["Valor de Potencia"].astype(str).str.replace(",", "."), errors="coerce"
    )
    df["monodroga"] = df["Código de monodroga"].astype(str).str.strip().str.lower()
    df["via"] = df["Código de vías de administración"].astype(str).str.strip().str.upper()
    df["precio"] = pd.to_numeric(
        df["Precio de Venta al Publico"].astype(str).str.replace(",", "."), errors="coerce"
    )
    df["ean"] = df["Código EAN/UPC"].astype(str).str.strip()
    df["cadena_frio"] = df["Cadena de frío"].fillna("").astype(str).str.strip()

    # Filtrar intraoculares
    mask_intraocular = df["via"].str.contains("INTRAOC", na=False) | df["Texto Largo de Material"].astype(str).str.contains("intraoc", case=False, na=False)
    df = df[~mask_intraocular].copy()

    return df


def presentaciones_como_dicts(catalogo: pd.DataFrame, farmaco: str) -> List[Dict]:
    """Convierte filas del catalogo Alfabeta a lista de dicts para resolver_presentaciones."""
    try:
        if catalogo is None or catalogo.empty:
            return []
        subset = catalogo[catalogo["monodroga"] == farmaco]
        records = []
        for _, row in subset.iterrows():
            records.append({
                "potencia_mg": row.get("potencia_mg"),
                "precio": row.get("precio"),
                "ean": row.get("ean", ""),
                "via": row.get("via", ""),
            })
        return records
    except Exception as exc:
        logger.error("Error en presentaciones_como_dicts(%s): %s", farmaco, exc, exc_info=True)
        raise


def generar_prescripcion(esqueleto: pd.DataFrame, catalogo: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Genera bloque B: prescripcion concordante para cada paciente."""
    print("\n=== SECCION 8-9: PRESCRIPCION DESDE GUIAS + DOSIS ===")

    filas = []
    for idx, pac in esqueleto.iterrows():
        id_regimen, base_regimen, reglas = regimen_por_guias(pac.to_dict())

        # Determinar farmacos del regimen
        farmacos_regimen = list(REGIMENES[id_regimen]["farmacos"])
        if id_regimen in ("R07", "R08") and base_regimen != id_regimen:
            farmacos_regimen = list(REGIMENES[base_regimen]["farmacos"]) + list(REGIMENES[id_regimen]["farmacos"])

        # Linea de tratamiento
        linea = 1
        if pac["estadio"] == 4 and rng.random() < 0.15:
            linea = 2

        bsa = pac["superficie_corporal_m2"]
        peso = pac["peso_kg"]
        costo_total = 0.0
        excedente_total = 0.0
        componentes = []

        for farmaco in farmacos_regimen:
            dosis_mg = calcular_dosis_mg(farmaco, bsa, peso, id_regimen)
            if dosis_mg <= 0:
                continue
            presentaciones = presentaciones_como_dicts(catalogo, farmaco)
            pres = resolver_presentaciones(dosis_mg, farmaco, presentaciones)
            costo_total += pres["costo"]
            excedente_total += pres["excedente_mg"]
            componentes.append({
                "farmaco": farmaco,
                "dosis_requerida_mg": round(dosis_mg, 2),
                "mg_cubiertos": pres["mg_cubiertos"],
                "excedente_mg": round(pres["excedente_mg"], 2),
                "costo": round(pres["costo"], 2),
            })

        fila = pac.to_dict()
        fila["id_regimen"] = id_regimen
        fila["base_regimen"] = base_regimen
        fila["linea_tratamiento"] = linea
        fila["costo_total_ars"] = round(costo_total, 2)
        fila["excedente_total_mg"] = round(excedente_total, 2)
        fila["n_farmacos"] = len(componentes)
        fila["reglas_aplicadas"] = "|".join(reglas)
        fila["es_valido"] = 1
        fila["tipo_error"] = 0

        # Features descompuestas del bloque B
        fila["tiene_anti_egfr"] = int(any(f in ["cetuximab", "panitumumab"] for f in farmacos_regimen))
        fila["tiene_antiangiogenico"] = int("bevacizumab" in farmacos_regimen)
        fila["es_inmunoterapia"] = int(any(f in ["pembrolizumab", "nivolumab", "ipilimumab"] for f in farmacos_regimen))
        fila["es_dirigido"] = int("encorafenib" in farmacos_regimen)
        fila["excedente_relativo"] = 0.0
        if componentes:
            total_req = sum(c["dosis_requerida_mg"] for c in componentes)
            if total_req > 0:
                fila["excedente_relativo"] = round(excedente_total / total_req, 4)

        filas.append(fila)

    df = pd.DataFrame(filas)
    print(f"  Prescripciones concordantes generadas: {len(df)}")
    print(f"  Distribucion de regimenes: {df['id_regimen'].value_counts().to_dict()}")
    return df


# ============================================================================
# SECCION 10-11: INYECCION DE ERRORES
# ============================================================================

def inyectar_errores(df_concordante: pd.DataFrame, catalogo: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Inyecta errores segun taxonomia cerrada."""
    print("\n=== SECCION 10-11: INYECCION DE ERRORES ===")

    n_concordantes = len(df_concordante)
    n_errores_target = int(n_concordantes * (1 - PROP_CONCORDANTES) / PROP_CONCORDANTES)
    n_fuera_reglas = int(n_errores_target * FRAC_ERRORES_FUERA_DE_REGLAS)
    n_dentro_reglas = n_errores_target - n_fuera_reglas

    filas_error = []
    tipos_error = [1, 2, 3, 4, 5, 6]
    nombres_error = {
        0: "sin_error", 1: "dosis_incorrecta",
        2: "discordancia_diagnostico_tratamiento",
        3: "esquema_no_concordante_estadificacion",
        4: "documentacion_incompleta",
        5: "combinacion_clinicamente_imposible",
        6: "medicamento_faltante",
    }

    # Errores dentro de reglas
    for i in range(n_dentro_reglas):
        idx = rng.integers(0, n_concordantes)
        fila = df_concordante.iloc[idx].copy().to_dict()
        tipo = tipos_error[i % len(tipos_error)]

        fila["es_valido"] = 0
        fila["tipo_error"] = tipo
        fila["id_paciente_base"] = fila.get("id_paciente_base", f"ERR_{i:04d}")

        if tipo == 1:  # Dosis incorrecta
            fila["excedente_relativo"] = round(rng.uniform(0.25, 0.6), 3)
            fila["excedente_total_mg"] = round(fila.get("excedente_total_mg", 0) * rng.uniform(3, 8), 2)

        elif tipo == 2:  # Discordancia diagnostico-tratamiento
            if fila.get("ras") == "mutado":
                fila["tiene_anti_egfr"] = 1
                fila["id_regimen"] = "R08"
            elif fila.get("msi") == "MSS":
                fila["es_inmunoterapia"] = 1
                fila["id_regimen"] = "R09"
            else:
                fila["tiene_anti_egfr"] = 1
                fila["id_regimen"] = "R08"

        elif tipo == 3:  # Esquema no concordante con estadificacion
            if fila.get("estadio") == 1:
                fila["id_regimen"] = "R01"
                fila["n_farmacos"] = 3
            else:
                fila["id_regimen"] = "R00"
                fila["n_farmacos"] = 0

        elif tipo == 4:  # Documentacion incompleta
            campos_borrar = rng.choice(["superficie_corporal_m2", "msi", "ras", "lateralidad"])
            fila[campos_borrar] = np.nan

        elif tipo == 5:  # Combinacion clinicamente imposible
            fila["m"] = "M1"
            fila["estadio"] = 1

        elif tipo == 6:  # Medicamento faltante
            fila["id_regimen"] = "R07"
            fila["tiene_antiangiogenico"] = 1
            fila["n_farmacos"] = max(fila.get("n_farmacos", 1) + 1, 4)

        filas_error.append(fila)

    # Errores fuera de reglas (para medir delta del ML)
    for i in range(n_fuera_reglas):
        idx = rng.integers(0, n_concordantes)
        fila = df_concordante.iloc[idx].copy().to_dict()
        tipo = rng.choice([1, 2, 3])

        fila["es_valido"] = 0
        fila["tipo_error"] = tipo
        fila["id_paciente_base"] = fila.get("id_paciente_base", f"ERRX_{i:04d}")

        if tipo == 1:  # Dosis desviada 8-15% (bajo tolerancia regla)
            fila["excedente_relativo"] = round(rng.uniform(0.08, 0.15), 3)
            fila["excedente_total_mg"] = round(fila.get("excedente_total_mg", 0) * rng.uniform(1.5, 2.5), 2)
        elif tipo == 2:  # Regimen valido pero de otro estadio
            if fila.get("estadio") == 4:
                fila["id_regimen"] = "R01"  # Adyuvancia en metastasico
            elif fila.get("estadio") == 3:
                fila["id_regimen"] = "R09"  # Inmunoterapia en adyuvancia
        elif tipo == 3:  # Lateralidad incorrecta para la terapia
            if fila.get("lateralidad") == "derecho":
                fila["tiene_anti_egfr"] = 1
                fila["tiene_antiangiogenico"] = 0

        filas_error.append(fila)

    df_errores = pd.DataFrame(filas_error)
    dataset = pd.concat([df_concordante, df_errores], ignore_index=True)

    print(f"  Errores dentro de reglas: {n_dentro_reglas}")
    print(f"  Errores fuera de reglas: {n_fuera_reglas}")
    print(f"  Dataset total: {len(dataset)} filas")
    print(f"  Balance: {dataset['es_valido'].value_counts().to_dict()}")
    print(f"  Tipos de error: {dataset['tipo_error'].value_counts().to_dict()}")

    return dataset


# ============================================================================
# SECCION 12: MODELO Y EVALUACION
# ============================================================================

def _capa_reglas(df: pd.DataFrame) -> np.ndarray:
    """Aplica reglas via backend.ml.reglas y devuelve 1=OK / 0=rechazo."""
    try:
        pred = np.ones(len(df), dtype=int)
        for i, (_, row) in enumerate(df.iterrows()):
            motivos = aplicar_reglas(row.to_dict())
            if motivos:
                pred[i] = 0
        return pred
    except Exception as exc:
        logger.error("Error en _capa_reglas: %s", exc, exc_info=True)
        raise


def entrenar_y_evaluar(
    dataset: pd.DataFrame,
    dir_artefactos: Path,
    rng: np.random.Generator,
    dir_figuras: Optional[Path] = None,
) -> Dict:
    """Entrena LightGBM con validacion correcta y reporta metricas."""
    print("\n=== SECCION 12: MODELO Y EVALUACION ===")

    X = preparar_features_dataframe(dataset)
    y = dataset["es_valido"].astype(int).values
    groups = dataset["id_paciente_base"].values

    # Capa de reglas como baseline
    pred_reglas = _capa_reglas(dataset)
    recall_reglas = recall_score(y == 0, pred_reglas == 0)
    print(f"  Capa de reglas sola - Recall no concordante: {recall_reglas:.4f}")

    # Validacion cruzada con StratifiedGroupKFold
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=int(rng.integers(1e6)))

    # LightGBM
    y_proba_lgb = np.zeros(len(y), dtype=float)
    y_pred_lgb = np.zeros(len(y), dtype=int)

    n_pos = (y == 1).sum()
    n_neg = (y == 0).sum()
    scale_pos = n_neg / max(n_pos, 1)

    for fold, (train_idx, val_idx) in enumerate(sgkf.split(X, y, groups)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        dtrain = lgb.Dataset(X_train, label=y_train)
        dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)

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
            "seed": int(rng.integers(1e6)),
        }

        model = lgb.train(
            params, dtrain,
            num_boost_round=300,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(30, verbose=False)],
        )

        y_proba_lgb[val_idx] = model.predict(X_val)
        y_pred_lgb[val_idx] = (y_proba_lgb[val_idx] >= 0.5).astype(int)

    # Calibracion isotonica
    from sklearn.isotonic import IsotonicRegression
    iso_reg = IsotonicRegression(out_of_bounds="clip")
    iso_reg.fit(y_proba_lgb, y)
    y_proba_calibrada = iso_reg.predict(y_proba_lgb)

    # Dos umbrales
    sorted_proba = np.sort(y_proba_calibrada)
    t_bajo = float(np.percentile(sorted_proba[y == 0], 70))
    t_alto = float(np.percentile(sorted_proba[y == 1], 30))
    if t_bajo >= t_alto:
        t_bajo, t_alto = 0.35, 0.65

    # Metricas LightGBM
    recall_lgb = recall_score(y == 0, y_pred_lgb == 0)
    auc_roc = roc_auc_score(y, y_proba_calibrada)
    auc_pr = average_precision_score(1 - y, 1 - y_proba_calibrada)
    brier = brier_score_loss(y, y_proba_calibrada)

    # Recall a tasa de revision fija (20%)
    n_revision = int(len(y) * 0.20)
    indices_revision = np.argsort(y_proba_calibrada)[:n_revision]
    errores_en_revision = (y[indices_revision] == 0).sum()
    total_errores = (y == 0).sum()
    recall_at_20 = errores_en_revision / max(total_errores, 1)

    # Aporte incremental sobre reglas
    delta_recall = recall_lgb - recall_reglas

    # Baselines
    # Arbol de decision profundidad 3
    dt = DecisionTreeClassifier(max_depth=3, random_state=42)
    y_pred_dt = np.zeros(len(y), dtype=int)
    for train_idx, val_idx in sgkf.split(X, y, groups):
        dt.fit(X.iloc[train_idx], y[train_idx])
        y_pred_dt[val_idx] = dt.predict(X.iloc[val_idx])
    recall_dt = recall_score(y == 0, y_pred_dt == 0)

    # Regresion logistica
    lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    y_pred_lr = np.zeros(len(y), dtype=int)
    for train_idx, val_idx in sgkf.split(X, y, groups):
        lr.fit(X.iloc[train_idx], y[train_idx])
        y_pred_lr[val_idx] = lr.predict(X.iloc[val_idx])
    recall_lr = recall_score(y == 0, y_pred_lr == 0)

    # Recall por celda de decision
    recall_por_celda = {}
    if "estadio" in dataset.columns:
        for est in sorted(dataset["estadio"].dropna().unique()):
            mask_est = dataset["estadio"] == est
            if mask_est.sum() > 0:
                y_est = y[mask_est]
                pred_est = y_pred_lgb[mask_est]
                if (y_est == 0).sum() > 0:
                    recall_por_celda[f"estadio_{int(est)}"] = float(recall_score(y_est == 0, pred_est == 0))

    # Metricas en subconjunto ambiguo
    recall_ambiguo = None
    if "es_ambiguo" in dataset.columns:
        mask_amb = dataset["es_ambiguo"] == True
        if mask_amb.sum() > 0:
            y_amb = y[mask_amb]
            pred_amb = y_pred_lgb[mask_amb]
            if (y_amb == 0).sum() > 0:
                recall_ambiguo = float(recall_score(y_amb == 0, pred_amb == 0))

    metricas = {
        "lgbm_recall_no_concordante": round(float(recall_lgb), 4),
        "lgbm_auc_roc": round(float(auc_roc), 4),
        "lgbm_auc_pr": round(float(auc_pr), 4),
        "lgbm_brier_score": round(float(brier), 4),
        "lgbm_recall_at_20pct_revision": round(float(recall_at_20), 4),
        "reglas_recall_no_concordante": round(float(recall_reglas), 4),
        "delta_ml_sobre_reglas": round(float(delta_recall), 4),
        "baseline_arbol_profundidad3_recall": round(float(recall_dt), 4),
        "baseline_logistica_recall": round(float(recall_lr), 4),
        "umbral_bajo": round(t_bajo, 4),
        "umbral_alto": round(t_alto, 4),
        "recall_por_celda": recall_por_celda,
        "recall_subconjunto_ambiguo": recall_ambiguo,
        "n_features": X.shape[1],
        "n_filas_entrenamiento": len(y),
    }

    print(f"\n  === RESULTADOS ===")
    print(f"  LightGBM recall no concordante: {recall_lgb:.4f}")
    print(f"  Reglas solas recall:            {recall_reglas:.4f}")
    print(f"  Delta ML sobre reglas:          {delta_recall:.4f}")
    print(f"  AUC-ROC: {auc_roc:.4f} | AUC-PR: {auc_pr:.4f} | Brier: {brier:.4f}")
    print(f"  Recall @ 20% revision: {recall_at_20:.4f}")
    print(f"  Arbol prof.3: {recall_dt:.4f} | Logistica: {recall_lr:.4f}")
    print(f"  Umbrales: t_bajo={t_bajo:.4f}, t_alto={t_alto:.4f}")

    # Entrenar modelo final
    dtrain_full = lgb.Dataset(X, label=y)
    model_final = lgb.train(params, dtrain_full, num_boost_round=200)

    # SHAP
    try:
        import shap
        explainer = shap.TreeExplainer(model_final)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        importance = np.abs(shap_values).mean(axis=0)
        feature_importance = dict(zip(X.columns, [round(float(v), 4) for v in importance]))
        metricas["shap_importance"] = dict(sorted(feature_importance.items(), key=lambda x: -x[1]))

        fig, ax = plt.subplots(figsize=(10, 6))
        sorted_imp = sorted(feature_importance.items(), key=lambda x: x[1])
        ax.barh([x[0] for x in sorted_imp], [x[1] for x in sorted_imp])
        ax.set_title("SHAP Feature Importance (mean |SHAP|)")
        plt.tight_layout()
        if dir_figuras is None:
            dir_figuras = dir_artefactos / "figuras"
        dir_figuras.mkdir(parents=True, exist_ok=True)
        plt.savefig(dir_figuras / "shap_importance.png", dpi=100)
        plt.close()
    except Exception as e:
        print(f"  Warning: SHAP fallo: {e}")

    # Guardar modelo
    dir_artefactos.mkdir(parents=True, exist_ok=True)
    artefacto = {
        "model": model_final,
        "calibrador": iso_reg,
        "umbrales": {"t_bajo": t_bajo, "t_alto": t_alto},
        "features": list(X.columns),
        "categorias": CATEGORIAS_MODELO,
        "version_modelo": "1.0.0",
    }
    joblib.dump(artefacto, dir_artefactos / "modelo_gbm.joblib")

    with open(dir_artefactos / "categorias_modelo.json", "w", encoding="utf-8") as f:
        json.dump(CATEGORIAS_MODELO, f, indent=2, ensure_ascii=False)

    with open(dir_artefactos / "metricas_modelo.json", "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False, default=str)

    return metricas


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Pipeline entrenamiento modelo colon - MedChain AI")
    parser.add_argument("--sin-red", action="store_true", help="Usar solo cache local")
    parser.add_argument("--semilla", type=int, default=SEMILLA, help="Semilla para reproducibilidad")
    parser.add_argument("--salida", type=str, default=None, help="Directorio de artefactos del modelo")
    args = parser.parse_args()

    rng = np.random.default_rng(args.semilla)
    script_dir = Path(__file__).resolve().parent
    cache_dir = script_dir / "cache"
    dir_artefactos = Path(args.salida) if args.salida else script_dir / "artefactos"
    dir_datos = script_dir / "datos"
    dir_figuras = script_dir / "figuras"
    dir_artefactos.mkdir(parents=True, exist_ok=True)
    dir_datos.mkdir(parents=True, exist_ok=True)
    dir_figuras.mkdir(parents=True, exist_ok=True)

    ruta_alfabeta = Path(__file__).resolve().parent.parent / "archivos_de_trabajo" / "Medicamentos v1.xlsx"
    if not ruta_alfabeta.exists():
        ruta_alfabeta = script_dir / "Medicamentos v1.xlsx"

    print("=" * 70)
    print("PIPELINE ENTRENAMIENTO MODELO - CANCER DE COLON")
    print("PFI UADE - MedChain AI")
    print("=" * 70)
    print(f"  Semilla: {args.semilla}")
    print(f"  Sin red: {args.sin_red}")
    print(f"  Artefactos: {dir_artefactos}")
    print(f"  Datos: {dir_datos}")
    print(f"  Figuras: {dir_figuras}")

    # SECCION 1-2: Extraccion y normalizacion
    tablas = extraer_datos(cache_dir, args.sin_red)
    tablas = normalizar_centinelas(tablas)

    # SECCION 3: Perfilado de calidad
    perfilar_calidad(tablas, dir_artefactos)

    # SECCION 4: EDA pasada 1 (cohorte real)
    print("\n=== SECCION 4: EDA ===")
    cases_flat = tablas["TCGA_COAD_cases"].copy()
    ejecutar_eda(cases_flat, "cohorte_tcga", dir_figuras, dir_artefactos)

    # SECCION 5: Esqueleto
    esqueleto = construir_esqueleto(tablas, rng)
    esqueleto.to_csv(dir_datos / "cohorte_esqueleto.csv", index=False)

    # SECCION 6-7: Re-estadificacion y ambiguos
    esqueleto_exp = reestadificar_y_ambiguos(esqueleto, rng)

    # SECCION 8-9: Prescripcion y dosis
    catalogo = cargar_catalogo_alfabeta(ruta_alfabeta) if ruta_alfabeta.exists() else pd.DataFrame()
    if catalogo.empty:
        print("  WARNING: Catalogo Alfabeta no encontrado, dosis seran aproximadas")
        catalogo = pd.DataFrame(columns=["monodroga", "potencia_mg", "precio", "ean", "via"])

    dataset_concordante = generar_prescripcion(esqueleto_exp, catalogo, rng)

    # SECCION 10-11: Errores
    dataset = inyectar_errores(dataset_concordante, catalogo, rng)

    # EDA pasada 2 (dataset generado)
    ejecutar_eda(dataset, "dataset_generado", dir_figuras, dir_artefactos)

    # Exportar dataset
    dataset.to_csv(dir_datos / "dataset_colon.csv", index=False)
    dataset.to_parquet(dir_datos / "dataset_colon.parquet", index=False)

    # Diccionario de codificacion (congelado + taxonomia de errores)
    diccionario = {
        "categorias_modelo": CATEGORIAS_MODELO,
        "tipo_error": {
            "sin_error": 0, "dosis_incorrecta": 1,
            "discordancia_diagnostico_tratamiento": 2,
            "esquema_no_concordante_estadificacion": 3,
            "documentacion_incompleta": 4,
            "combinacion_clinicamente_imposible": 5,
            "medicamento_faltante": 6,
        },
        "regimenes": {k: v["nombre"] for k, v in REGIMENES.items()},
    }
    with open(dir_artefactos / "diccionario_codificacion.json", "w", encoding="utf-8") as f:
        json.dump(diccionario, f, indent=2, ensure_ascii=False)

    # SECCION 12: Modelo
    metricas = entrenar_y_evaluar(dataset, dir_artefactos, rng, dir_figuras=dir_figuras)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETADO")
    print("=" * 70)
    print(f"  Esqueleto: {len(esqueleto)} pacientes reales")
    print(f"  Esqueleto expandido: {len(esqueleto_exp)} pacientes")
    print(f"  Dataset final: {len(dataset)} filas")
    print(f"  Artefactos en: {dir_artefactos}")
    print(f"  Datos en: {dir_datos}")
    print("=" * 70)


if __name__ == "__main__":
    main()
