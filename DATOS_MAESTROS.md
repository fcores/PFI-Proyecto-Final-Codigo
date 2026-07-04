# Datos Maestros — MedChain AI

Documentación de todas las entidades del proyecto (backend FastAPI). Incluye los campos, tipos, obligatoriedad, identificadores, relaciones, endpoints y columnas de importación por Excel de cada entidad.

> Persistencia: todas las entidades se almacenan **en memoria** (se reinician al reiniciar el backend). La API corre en `http://127.0.0.1:9999`.

## Índice de entidades

| Entidad | Prefijo API | Código / ID | Importación Excel |
|---------|-------------|-------------|-------------------|
| [Paciente](#1-paciente-patient) | `/patients` | `id` autoincremental | Sí |
| [Empadronamiento](#2-empadronamiento-enrollment) | `/enrollments` | `EMP-{A\|B}-0000` | Sí (por tipo) |
| [Acuerdo](#3-acuerdo-agreement) | `/agreements` | `id` autoincremental | Sí |
| [Medicamento](#4-medicamento-medication) | `/medications` | `id` autoincremental | Sí |
| [Monodroga](#5-monodroga-monodrug) | `/monodrugs` | `id` autoincremental | Sí |
| [Prescripción](#6-prescripción-prescription) | `/prescriptions` | `PRESC-0000` | No |
| [Bloque / Ledger](#7-bloque--ledger-blockchain-simulada) | `/ledger` | `index` + `hash` | No |
| [Usuario / Sesión](#8-usuario--sesión-auth) | `/auth` | `username` | No |
| [Resultado de importación](#9-resultado-de-importación-bulkimportresult) | (transversal) | — | — |

---

## 1. Paciente (`Patient`)

Entidad clínica central. Combina datos del paciente con datos del empadronamiento inicial.

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
| `tipo_empadronamiento` | str | Sí | Tipo de empadronamiento |
| `fecha_inicio` | date | Sí | Fecha de inicio del empadronamiento |
| `fecha_primera_toma` | date | Sí | Fecha de la primera toma |
| `cadencia_estimada_toma` | int | Sí (`>= 1`) | Cadencia en días |
| `id` | int | (auto) | Identificador autoincremental |
| `hc_filename` | str | No | Nombre de archivo: historia clínica |
| `ap_filename` | str | No | Nombre de archivo: anatomía patológica |
| `img_filename` | str | No | Nombre de archivo: imágenes |
| `lab_filename` | str | No | Nombre de archivo: laboratorio |
| `receta_filename` | str | No | Nombre de archivo: receta |
| `otros_filename` | str | No | Nombre de archivo: otros |
| `blockchain_tx_id` | str | No | ID de transacción en blockchain (placeholder) |

**Relaciones:** `provider`/`provider_id` (prestador), `medications` (lista de descripciones, no FK), `tipo_empadronamiento` alineado con Empadronamiento.

**Endpoints:**
- `POST /patients` — alta (multipart/form-data: datos + 6 archivos opcionales).
- `GET /patients` — listado.
- `POST /patients/bulk-import` — importación desde `.xlsx`.

**Columnas Excel (alias aceptados):**
- `sap_id`: "id paciente sap", "sap", "id sap paciente"
- `credential_id`: "id credencial", "credencial"
- `provider_id`: "id prestador"
- `provider`: "prestador"
- `first_name`: "nombre"
- `last_name`: "apellido"
- `birth_date`: "fecha de nacimiento", "fecha_nacimiento"
- `gender`: "genero", "sexo"
- `treatment`: "diagnostico", "tratamiento"
- `tipo_empadronamiento`: "tipo de empadronamiento", "tipo_empadronamiento"

> En importación por Excel, `medications` se carga vacío (`[]`).

---

## 2. Empadronamiento (`Enrollment`)

Registro de empadronamiento por esquema de tratamiento, particionado por **tipo**.

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `medications` | list[str] | Sí (`min 1`) | Medicamentos |
| `diagnostico` | str | Sí | Diagnóstico |
| `id` | int | (auto) | Autoincremental por tipo |
| `enrollment_code` | str | (auto) | Formato `EMP-{A\|B}-0001` |
| `tipo` | str | (ruta) | `tipo-a` o `tipo-b` |
| `created_at` | datetime | (auto) | Fecha de creación |
| `blockchain_tx_id` | str | No | Placeholder |

**Tipos válidos:** `tipo-a`, `tipo-b` (un tipo inexistente devuelve 404).

**Endpoints:**
- `POST /enrollments/{tipo}` — alta.
- `GET /enrollments/{tipo}` — listado por tipo.
- `POST /enrollments/{tipo}/bulk-import` — importación por tipo.

**Columnas Excel:**
- `diagnostico`: "diagnostico", "diagnóstico"
- `medications`: "medications", "medicamentos", "medicamento" (separadores `;` `,` `|`)

---

## 3. Acuerdo (`Agreement`)

Convenio comercial laboratorio–prestador–medicamento.

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `laboratorio` | str | Sí | |
| `prestador` | str | Sí | |
| `medicamento` | str | Sí | |
| `medicamento_sap` | str | Sí | |
| `medico_auditor` | str | No | |
| `fecha_inicial` | date | Sí | |
| `fecha_final` | date | Sí | |
| `condicion_recupero` | str | Sí | |
| `id` | int | (auto) | Autoincremental |
| `contrato_filename` | str | No | Nombre de archivo del contrato |

**Endpoints:**
- `POST /agreements` — alta (+ contrato opcional).
- `GET /agreements` — listado.
- `POST /agreements/bulk-import` — importación.

**Columnas Excel:**
- `laboratorio`: "laboratorio"
- `prestador`: "prestador"
- `medicamento`: "medicamento"
- `medicamento_sap`: "medicamento sap", "medicamento_sap"
- `medico_auditor`: "medico auditor", "medico_auditor"
- `fecha_inicial`: "fecha inicial", "fecha_inicial"
- `fecha_final`: "fecha final", "fecha_final"
- `condicion_recupero`: "condicion recupero", "condición recupero", "condicion de recupero"

---

## 4. Medicamento (`Medication`)

Maestro de materiales / medicamentos.

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `descripcion` | str | Sí | |
| `ean` | str | Sí | Código de barras EAN |
| `codigo_alfabeta` | str | Sí | Código Alfabeta |
| `tipo_conservacion` | str | Sí | Ej.: `seco`, `frio` |
| `sap_id` | str | Sí | ID SAP |
| `monodroga_id` | str | Sí | Referencia a `Monodrug.sap_id` |
| `tamano_dimension` | str | Sí | Tamaño / dimensión |
| `id` | int | (auto) | Autoincremental |
| `monodroga_descripcion` | str | (derivado) | Resuelto en runtime por `monodroga_id == Monodrug.sap_id` |

**Relación:** `monodroga_id` → `Monodrug.sap_id` (lookup en memoria).

**Endpoints:**
- `POST /medications` — alta.
- `GET /medications` — listado (enriquecido con `monodroga_descripcion`).
- `POST /medications/bulk-import` — importación.

**Columnas Excel:**
- `descripcion`: "descripcion", "descripción"
- `ean`: "ean"
- `codigo_alfabeta`: "codigo alfabeta", "código alfabeta", "codigo_alfabeta"
- `tipo_conservacion`: "tipo conservacion", "tipo de conservacion", "tipo_conservacion"
- `sap_id`: "sap_id", "id sap"
- `monodroga_id`: "monodroga_id", "id monodroga", "id de monodroga"
- `tamano_dimension`: "tamano dimension", "tamaño dimension", "tamano_dimension", "tamaño/dimension"

---

## 5. Monodroga (`Monodrug`)

Principio activo / maestro farmacológico.

| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `descripcion` | str | Sí | |
| `sap_id` | str | Sí | ID SAP (referenciado por medicamentos) |
| `id` | int | (auto) | Autoincremental |

**Endpoints:**
- `POST /monodrugs` — alta.
- `GET /monodrugs` — listado.
- `POST /monodrugs/bulk-import` — importación.

**Columnas Excel:**
- `descripcion`: "descripcion", "descripción"
- `sap_id`: "sap_id", "id sap", "idsap"

---

## 6. Prescripción (`Prescription`)

Prescripción oncológica de alta complejidad (caso piloto: cáncer de colon). Al crearse, ejecuta la validación (motor stub) y registra un bloque en el ledger.

### Atributos de paciente y dosis
| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `patient_sap_id` | str | Sí | ID Paciente SAP |
| `edad` | int | Sí (`0–120`) | |
| `sexo` | str | Sí | Masculino / Femenino |
| `peso_kg` | float | Sí (`> 0`) | |
| `talla_cm` | float | Sí (`> 0`) | |
| `superficie_corporal_m2` | float | (derivado) | Mosteller: `sqrt(talla_cm * peso_kg / 3600)` |

### Estadificación TNM
| Campo | Tipo | Obligatorio | Valores |
|-------|------|-------------|---------|
| `diagnostico_cie10` | str | Sí | Ej.: `C18.9` |
| `localizacion_tumor` | str | Sí | Colon derecho / Colon izquierdo |
| `tipo_histologico` | str | Sí | Ej.: Adenocarcinoma |
| `t` | str | Sí | T1, T2, T3, T4 |
| `n` | str | Sí | N0, N1, N2 |
| `m` | str | Sí | M0, M1 |
| `estadio` | str | Sí | I, II, III, IV |

### Biomarcadores
| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `msi_alta` | bool | No (`false`) | Inestabilidad microsatelital alta |
| `ras_mutado` | bool | No (`false`) | KRAS/NRAS mutado |
| `braf_v600e` | bool | No (`false`) | BRAF V600E presente |

### Prescripción
| Campo | Tipo | Obligatorio | Notas |
|-------|------|-------------|-------|
| `linea_tratamiento` | str | Sí | Primera / Segunda |
| `esquema` | str | Sí | Esquema y medicamento prescrito |
| `dosis_mg_m2` | float | Sí (`> 0`) | Dosis en mg/m² |
| `medico_prescriptor` | str | Sí | |
| `matricula` | str | Sí | |

### Campos generados
| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | Autoincremental |
| `prescription_code` | str | Formato `PRESC-0001` |
| `created_at` | datetime | Fecha de creación |
| `validacion` | ValidationResult | Resultado de la validación |
| `blockchain_tx_id` | str | Hash del bloque en el ledger |
| `block_index` | int | Índice del bloque |

### `ValidationResult`
| Campo | Tipo | Notas |
|-------|------|-------|
| `estado` | str | `APROBADO` / `RECHAZADO` / `REVISION` |
| `motivos` | list[str] | Motivos de la validación |

> Motor de validación: **stub** (completitud + linealidad, ej. estadio IV requiere M1). Criterio recall-first: ante duda deriva a `REVISION`.

**Endpoints:**
- `POST /prescriptions` — alta (JSON).
- `GET /prescriptions` — listado.

---

## 7. Bloque / Ledger (blockchain simulada)

Registro inmutable simulado: cadena de bloques enlazados por hash SHA-256 en memoria.

### `Block`
| Campo | Tipo | Notas |
|-------|------|-------|
| `index` | int | Índice del bloque (0 = génesis) |
| `timestamp` | str | Marca de tiempo ISO |
| `tx_type` | str | `genesis`, `prescription`, ... |
| `payload` | dict | Contenido de la transacción |
| `prev_hash` | str | Hash del bloque anterior |
| `hash` | str | SHA-256 de `index+timestamp+tx_type+payload+prev_hash` |

### `LedgerVerification`
| Campo | Tipo | Notas |
|-------|------|-------|
| `valido` | bool | La cadena es íntegra |
| `total_bloques` | int | Cantidad de bloques |
| `roto_en` | int? | Índice del primer bloque inválido (o `null`) |

**Endpoints:**
- `GET /ledger` — lista de bloques.
- `GET /ledger/verify` — verificación de integridad.

---

## 8. Usuario / Sesión (`Auth`)

Autenticación simple del prototipo. Credenciales leídas desde variables de entorno (`.env`); tokens opacos en memoria.

### `LoginRequest`
| Campo | Tipo | Obligatorio |
|-------|------|-------------|
| `username` | str | Sí |
| `password` | str | Sí |

### `UserInfo`
| Campo | Tipo | Notas |
|-------|------|-------|
| `username` | str | Usuario |
| `display_name` | str | Nombre a mostrar |

### `LoginResponse`
| Campo | Tipo | Notas |
|-------|------|-------|
| `token` | str | Token de sesión (Bearer) |
| `user` | UserInfo | Usuario autenticado |

**Variables de entorno (`.env`):** `AUTH_USERNAME`, `AUTH_PASSWORD`, `AUTH_DISPLAY_NAME`.

**Endpoints:**
- `POST /auth/login` — login (JSON).
- `GET /auth/me` — usuario actual (header `Authorization: Bearer <token>`).
- `POST /auth/logout` — cierre de sesión.

---

## 9. Resultado de importación (`BulkImportResult`)

Estructura transversal devuelta por todos los endpoints `/*/bulk-import`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `total_rows` | int | Total de filas procesadas |
| `imported_count` | int | Registros importados |
| `failed_count` | int | Registros fallidos |
| `errors` | list[BulkImportError] | Detalle de errores |

### `BulkImportError`
| Campo | Tipo | Notas |
|-------|------|-------|
| `row_number` | int | Fila del Excel (desde 2 = primera fila de datos) |
| `message` | str | Descripción del error |

> Formato de importación: solo `.xlsx`. Fechas aceptadas como `date`/`datetime`/`Timestamp` o string ISO `YYYY-MM-DD`. Listas con separadores `;`, `,` o `|`. Los errores por fila se acumulan sin abortar el resto.
