# Datos Maestros — MedChain AI

Documentación de las entidades del proyecto (backend FastAPI). Incluye campos, tipos, obligatoriedad, identificadores, relaciones, endpoints y columnas de importación por Excel.

> Persistencia: PostgreSQL si está configurado; si no, **en memoria** (se reinicia al reiniciar el backend). La API corre en `http://127.0.0.1:9999`.

## Índice de entidades

| Entidad | Prefijo API | Código / ID | Importación Excel |
|---------|-------------|-------------|-------------------|
| [Paciente](#1-paciente-patient) | `/patients` | `id` autoincremental | Sí |
| [Medicamento](#2-medicamento-medication) | `/medications` | `MED-0001` (auto) | Sí |
| [Monodroga](#3-monodroga-monodrug) | `/monodrugs` | `MONO-0001` (auto) | Sí |
| [Prescripción](#4-prescripción-prescription) | `/prescriptions` | `PRESC-0000` | No |
| [Bloque / Ledger](#5-bloque--ledger-blockchain-simulada) | `/ledger` | `index` + `hash` | No |
| [Usuario / Sesión](#6-usuario--sesión-auth) | `/auth` | `username` | No |
| [Resultado de importación](#7-resultado-de-importación-bulkimportresult) | (transversal) | — | — |

> **Eliminado del proceso:** Empadronamientos y Acuerdos ya no forman parte del sistema.

---

## 1. Paciente (`Patient`)

Entidad clínica central.

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `sap_id` | str | Sí | ID Paciente SAP |
| `credential_id` | str | No | ID Credencial |
| `provider_id` | str | No | ID Prestador |
| `provider` | str | No | Prestador |
| `first_name` | str | Sí | Nombre |
| `last_name` | str | Sí | Apellido |
| `birth_date` | date | Sí | Fecha de nacimiento (`YYYY-MM-DD`) |
| `gender` | str | Sí | Género |
| `treatment` | str | No | Tratamiento / diagnóstico |
| `medications` | list[str] | No (`[]`) | Medicamentos |
| `id` | int | (auto) | Identificador autoincremental |
| `hc_filename` / `ap_filename` / `img_filename` / `lab_filename` / `receta_filename` / `otros_filename` | str | No | Adjuntos |
| `blockchain_tx_id` | str | No | Placeholder blockchain |

**Endpoints:**
- `POST /patients` — alta (multipart/form-data).
- `GET /patients` — listado.
- `POST /patients/bulk-import` — importación desde `.xlsx`.

**Columnas Excel:** `sap_id`, `credential_id`, `provider_id`, `provider`, `first_name`, `last_name`, `birth_date`, `gender`, `treatment`.

---

## 2. Medicamento (`Medication`)

Maestro de materiales / presentaciones. Atributos alineados con `Medicamentos v1.xlsx`.

| Campo | Tipo | Obligatorio | Notas / columna xlsx |
|-------|------|-------------|----------------------|
| `codigo` | str | (auto) | `MED-0001`, `MED-0002`, … |
| `descripcion` | str | Sí | Texto Largo de Material |
| `ean` | str | Sí | Código EAN/UPC |
| `codigo_alfabeta` | str | Sí | Nro Troquel alfabeta |
| `tipo_conservacion` | str | Sí | Cadena de frío (`frio` / `seco`; en Excel `X` → frío) |
| `laboratorio` | str | Sí | Laboratorio |
| `monodroga` | str | Sí | Nombre de la droga (debe existir en maestro de monodrogas) |
| `tamano_dimension` | str | Sí | Tamaño / Dimensión |
| `potencia_mg` | float | No | Valor de Potencia |
| `unidad_potencia` | str | No | Códigos de Potencia (ej. `MG`) |
| `precio` | float | No | Precio de Venta al Público |
| `via_administracion` | str | No | Código de vías (`ORAL`, `INYECTABLE IV`, …) |
| `id` | int | (auto) | Autoincremental |

**Relación:** `monodroga` → `Monodrug.descripcion` (validada en alta individual). En bulk import, si la monodroga no existe se **auto-crea**.

**Endpoints:**
- `POST /medications` — alta.
- `GET /medications` — listado.
- `POST /medications/bulk-import` — importación (acepta headers del xlsx real).

**Uso en costos:** `DosisService.find_by_monodroga(nombre)` busca presentaciones por este campo para calcular dosis y costo.

---

## 3. Monodroga (`Monodrug`)

Principio activo / maestro farmacológico.

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `descripcion` | str | Sí | Nombre de la droga (ej. `oxaliplatino`, `pembrolizumab`) |
| `codigo` | str | (auto) | `MONO-0001`, `MONO-0002`, … |
| `id` | int | (auto) | Autoincremental |

**Endpoints:**
- `POST /monodrugs` — alta (solo `descripcion`; código auto).
- `GET /monodrugs` — listado (usado por el desplegable del alta de medicamentos).
- `POST /monodrugs/bulk-import` — importación.

**Columnas Excel:** `descripcion` (también acepta “código de monodroga”).

---

## 4. Prescripción (`Prescription`)

Prescripción oncológica de alta complejidad (cáncer de colon). Al crearse, ejecuta validación híbrida (reglas + LightGBM) y registra un bloque en el ledger.

### Atributos de paciente y dosis
| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `patient_sap_id` | str | Sí | ID Paciente SAP |
| `edad` | int | Sí (`0–120`) | |
| `sexo` | str | Sí | Masculino / Femenino |
| `peso_kg` / `talla_cm` | float | Sí (`> 0`) | |
| `superficie_corporal_m2` | float | (derivado) | Mosteller |
| `id_regimen` | str | Sí | R00–R13 |
| `dosis_por_farmaco` | list | No | `{monodroga, dosis_mg}` |
| `msi` / `ras` / `braf_v600e` | Literal | Sí | Tres estados (incl. `no_evaluado`) |

### `ValidationResult` (resumen)
| Campo | Tipo | Notas |
|-------|------|-------|
| `estado` | str | `APROBADO` / `RECHAZADO` / `REVISION` |
| `motivos` | list[str] | |
| `probabilidad_concordante` | float | Score del modelo |
| `costo_por_farmaco` / `costo_total` | list / float | Estimado desde el catálogo |

**Endpoints:**
- `POST /prescriptions` — alta (JSON).
- `GET /prescriptions` — listado.
- `GET /prescriptions/regimenes` — catálogo.
- `GET /prescriptions/dosis-referencia` — dosis de referencia.
- `POST /prescriptions/recomendacion` — sugerencia por guías (sin ML).

---

## 5. Bloque / Ledger (blockchain simulada)

Registro inmutable simulado: cadena de bloques enlazados por hash SHA-256.

**Endpoints:** `GET /ledger`, `GET /ledger/verify`.

---

## 6. Usuario / Sesión (`Auth`)

Credenciales desde `.env` (`AUTH_USERNAME`, `AUTH_PASSWORD`, `AUTH_DISPLAY_NAME`).

**Endpoints:** `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`.

---

## 7. Resultado de importación (`BulkImportResult`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `total_rows` | int | Filas procesadas |
| `imported_count` | int | Importados |
| `failed_count` | int | Fallidos |
| `errors` | list[BulkImportError] | Detalle por fila |

> Formato: solo `.xlsx`. En import de medicamentos, monodrogas faltantes se crean automáticamente.
