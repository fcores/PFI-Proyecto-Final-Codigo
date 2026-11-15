# ml_models — Entrenamiento MedChain AI

Modulo de construccion de dataset hibrido (TCGA-COAD + guias clinicas) y
entrenamiento del modelo LightGBM de validacion de prescripciones de cancer
de colon.

La logica compartida (regimenes, codificacion congelada, dosis, guias y reglas)
vive en `backend/ml/` para garantizar paridad train/serve.

## Dependencias

Desde la raiz del repositorio:

```bash
pip install -r ml_models/requirements-entrenamiento.txt
```

## Reentrenamiento rapido (sin red)

Usa el dataset ya generado en `ml_models/datos/` (CSV o parquet), codificacion
congelada y guarda el artefacto en `ml_models/artefactos/`:

```bash
python -m ml_models.reentrenar_desde_dataset
python -m ml_models.reentrenar_desde_dataset --semilla 42
```

## Pipeline completo

Regenera cache/dataset (opcional) y entrena. Con `--sin-red` solo usa
`ml_models/cache/` y no llama a HuggingFace/cBioPortal:

```bash
python -m ml_models.entrenar_modelo --sin-red
python -m ml_models.entrenar_modelo --semilla 42
```

Requiere el catalogo Alfabeta en:

`archivos_de_trabajo/Medicamentos v1.xlsx`

(con fallback a `ml_models/Medicamentos v1.xlsx`).

## Salidas

| Ruta | Contenido |
|------|-----------|
| `ml_models/datos/` | `dataset_colon.csv`, `dataset_colon.parquet`, esqueleto |
| `ml_models/artefactos/` | `modelo_gbm.joblib`, `categorias_modelo.json`, `metricas_modelo.json` |
| `ml_models/figuras/` | Graficos EDA / SHAP |
| `ml_models/cache/` | Parquets TCGA / cBioPortal |

El artefacto `modelo_gbm.joblib` incluye modelo, calibrador, umbrales,
features, `categorias` (encoding congelado) y `version_modelo`.
