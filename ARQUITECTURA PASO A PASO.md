# Arquitectura Paso a Paso - MedChain AI

## Tabla de contenidos

1. [Vision general del proyecto](#1-vision-general-del-proyecto)
2. [Estructura de carpetas](#2-estructura-de-carpetas)
3. [Frontend (React + Vite)](#3-frontend-react--vite)
4. [Backend (Python + FastAPI)](#4-backend-python--fastapi)
5. [Prescripciones on-chain (fuente de verdad en Fabric)](#5-prescripciones-on-chain-fuente-de-verdad-en-fabric)
6. [Blockchain privada (Hyperledger Fabric en EC2)](#6-blockchain-privada-hyperledger-fabric-en-ec2)
7. [Chaincode (Smart Contract en Go)](#7-chaincode-smart-contract-en-go)
8. [Despliegue en AWS](#8-despliegue-en-aws)
9. [CI/CD con GitHub Actions](#9-cicd-con-github-actions)
10. [Flujo completo: que pasa cuando se crea una prescripcion](#10-flujo-completo-que-pasa-cuando-se-crea-una-prescripcion)
11. [Proximo paso: conectar el backend con la blockchain real](#11-proximo-paso-conectar-el-backend-con-la-blockchain-real)
12. [Glosario de terminos](#12-glosario-de-terminos)
13. [Costos de AWS y como optimizarlos](#13-costos-de-aws-y-como-optimizarlos)

---

## 1. Vision general del proyecto

MedChain AI es una aplicacion web para la **auditoria de prescripciones oncologicas de alta complejidad**. Cada prescripcion pasa por un motor de validacion hibrido (reglas deterministicas + modelo LightGBM) como soporte de decision y se asienta **directamente en Hyperledger Fabric**, donde una red de tres organizaciones (prescriptor, auditora MedChain y prepaga) endosa cada transaccion y monitorea que no haya adulteraciones. Solo el auditor cierra el ciclo con su dictamen (aprobar / rechazar / revision), que tambien queda on-chain con un hash encadenado.

El sistema tiene tres componentes principales desplegados en AWS de forma independiente:

### Diagrama de arquitectura

```
                          Internet
                             |
                      +------+------+
                      |  CloudFront |
                      |   (HTTPS)   |
                      +------+------+
                        /         \
                       /           \
              +-------+---+   +----+----------+
              |    S3     |   | API Gateway   |
              | (Frontend)|   | HTTP API      |
              | React SPA |   +----+----------+
              +-----------+        |
                                   | VPC Link
                                   |
                            +------+------+
                            | ECS Fargate |
                            | (Backend)   |
                            | FastAPI     |
                            | Puerto 8000 |
                            +-------------+

              +---------------------------+
              |     EC2 (t3.large)        |
              |     Blockchain            |
              |     Hyperledger Fabric    |
              |     2.5 LTS              |
              |     Docker Compose        |
              +---------------------------+
```

**En palabras simples:**
- El **frontend** es lo que el usuario ve en el navegador (formularios, tablas, login).
- El **backend** recibe los datos, los valida, los registra en un ledger simulado (cadena de hashes SHA-256 en memoria) y devuelve el resultado.
- La **blockchain** (Hyperledger Fabric) es una red privada en una EC2 dedicada con chaincode en Go. Actualmente funciona de forma independiente; la integracion con el backend es el proximo paso.

### Stack tecnologico

| Capa | Tecnologia | Hosting AWS |
|------|-----------|-------------|
| **Frontend** | React 19 + Vite 6 | S3 + CloudFront |
| **Backend** | Python 3.12 + FastAPI | ECS Fargate + API Gateway HTTP API |
| **Persistencia** | PostgreSQL 15 (con fallback en memoria) | RDS o EC2 |
| **Autenticacion** | RBAC con hash+salt (3 roles) | Dentro del backend |
| **Validacion** | Motor de reglas (stub) | Dentro del backend |
| **Ledger simulado** | Cadena SHA-256 en memoria | Dentro del backend |
| **Blockchain** | Hyperledger Fabric 2.5 LTS | EC2 t3.large dedicada |
| **Smart Contract** | Go (contractapi) | Dentro de la red Fabric |
| **CI/CD** | GitHub Actions | GitHub |

---

## 2. Estructura de carpetas

```
PFI-Proyecto-Final/
|
|-- .github/workflows/       CI/CD con GitHub Actions
|   |-- deploy.yml           Deploy automatico a AWS al pushear a main
|
|-- backend/                  Servidor API en Python
|   |-- main.py               Punto de entrada (FastAPI + Uvicorn, version 0.5.0)
|   |-- db.py                 Conexion PostgreSQL (pool, context manager, fallback en memoria)
|   |-- auth_middleware.py    Middleware de autenticacion y RBAC (require_auth, require_role)
|   |-- dependencies.py       Inyeccion de dependencias (singleton repos/services)
|   |-- models/               Modelos Pydantic (patient, prescription, audit, agreement, enrollment, etc.)
|   |-- repositories/         Repositorios con soporte dual PostgreSQL / en memoria
|   |-- routers/              Endpoints bajo /api con autenticacion y control de roles
|   |   |-- auth_router.py       Autenticacion (login, me, logout)
|   |   |-- patient_router.py    CRUD de pacientes
|   |   |-- prescription_router.py  Prescripciones oncologicas
|   |   |-- ledger_router.py     Bloques del ledger y verificacion
|   |   |-- medication_router.py Medicamentos
|   |   |-- monodrug_router.py   Monodrogas
|   |   |-- agreement_router.py  Acuerdos con laboratorios
|   |   |-- enrollment_router.py Empadronamientos
|   |   |-- audit_router.py     Cola de auditoria, dictamenes, correcciones
|   |-- services/             Logica de negocio
|       |-- auth_service.py      Autenticacion con hash+salt (BD o fallback .env)
|       |-- prescription_service.py  Validacion + registro en ledger + caso de auditoria
|       |-- validation_service.py    Motor de reglas (stub)
|       |-- ledger_service.py       Cadena de bloques SHA-256
|       |-- audit_service.py        Gestion de casos, dictamenes y correcciones
|       |-- patient_service.py
|       |-- medication_service.py
|       |-- monodrug_service.py
|       |-- agreement_service.py
|       |-- enrollment_service.py
|       |-- excel_import_service.py
|
|-- sql/                      Queries SQL externalizadas
|   |-- schema.sql            DDL de 11 tablas (users, patients, prescriptions, audit_cases, etc.)
|   |-- patients.sql          Queries CRUD de pacientes
|   |-- prescriptions.sql     Queries de prescripciones
|   |-- audit.sql             Queries de auditoria (casos, dictamenes, correcciones)
|   |-- agreements.sql        Queries de acuerdos
|   |-- enrollments.sql       Queries de empadronamientos
|   |-- medications.sql       Queries de medicamentos
|   |-- monodrugs.sql         Queries de monodrogas
|   |-- ledger.sql            Queries del ledger
|   |-- users.sql             Queries de usuarios
|
|-- frontend/                 Aplicacion web React
|   |-- index.html
|   |-- vite.config.js        Dev server + proxy /api al backend
|   |-- package.json
|   |-- src/
|       |-- App.jsx            Rutas de la SPA con proteccion RBAC
|       |-- main.jsx           Punto de entrada
|       |-- index.css          Estilos globales
|       |-- api/
|       |   |-- client.js      API_BASE configurable (VITE_API_URL || "/api")
|       |   |-- audit.js       Cliente de la API de auditoria
|       |   |-- agreements.js  Cliente de la API de acuerdos
|       |   |-- enrollments.js Cliente de la API de empadronamientos
|       |-- auth/
|       |   |-- ProtectedRoute.jsx  Proteccion de rutas con soporte de roles
|       |   |-- AuthContext.jsx     Contexto de autenticacion (user con role)
|       |-- components/        Componentes reutilizables (Layout, Sidebar por roles, etc.)
|       |-- hooks/             Hooks personalizados
|       |-- pages/             Paginas de la aplicacion (auditoria, trazabilidad, usuarios, salud)
|
|-- chaincode/                Smart Contract en Go (fuente de verdad de las prescripciones)
|   |-- prescription-contract/  contract.go, contract_test.go, indices CouchDB (META-INF)
|
|-- fabric-gateway-svc/       Puente HTTP -> Fabric Gateway SDK (una identidad por org)
|
|-- fabric/                   Infraestructura de la red Hyperledger Fabric (3 orgs + CouchDB)
|   |-- network.sh            Punto de entrada (install, up, createChannel, deployCC, down)
|   |-- network/              crypto-config, configtx, compose, .env (.env.example versionado)
|   |-- scripts/              bootstrap, createChannel, deployChaincode, etc.
|
|-- deploy/                   Scripts de despliegue automatizado en AWS (CLI)
|   |-- deploy-all.sh         Script maestro
|   |-- 00-variables.sh       Variables de configuracion
|   |-- 01-vpc-network.sh     VPC, subredes, Security Groups
|   |-- 02-ecr-push.sh        Build Docker + push a ECR
|   |-- 03-secrets-iam.sh     Secrets Manager + roles IAM
|   |-- 04-ecs-cluster.sh     ECS Fargate + Cloud Map
|   |-- 05-api-gateway.sh     API Gateway HTTP API + VPC Link
|   |-- 06-s3-cloudfront.sh   S3 + CloudFront (SPA + API)
|   |-- 99-cleanup.sh         Limpieza de recursos
|
|-- docs/                     Documentacion
|   |-- 01-prerequisitos.md
|   |-- 02-arquitectura.md
|   |-- 03-uso.md
|   |-- 04-aws-ec2-setup.md
|   |-- 05-deploy-aws-consola.md   Guia paso a paso para AWS por consola web
|
|-- ml_models/                Modulo de inteligencia artificial
|   |-- entrenar_modelo.py    Pipeline dataset + entrenamiento GBM
|   |-- reentrenar_desde_dataset.py  Reentrenamiento desde dataset local
|
|-- Dockerfile                Imagen Docker del backend
|-- .dockerignore             Exclusiones para Docker build
|-- requirements.txt          Dependencias de Python
|-- .gitignore                Archivos ignorados por Git
|-- README.md                 Documentacion principal
|-- DATOS_MAESTROS.md         Catalogo de datos maestros del dominio
```

---

## 3. Frontend (React + Vite)

### Que es

El frontend es la **interfaz grafica** que el usuario ve en su navegador.

| Tecnologia | Para que sirve |
|-----------|---------------|
| **React 19** | Libreria para construir interfaces con componentes |
| **Vite 6** | Servidor de desarrollo rapido y build para produccion |
| **react-router-dom 7** | Navegacion SPA (Single Page Application) |
| **xlsx** | Importacion masiva desde archivos Excel |

### Como funciona

1. El usuario abre la aplicacion en el navegador.
2. Si no esta autenticado, se muestra la pantalla de **login** (split-screen).
3. Al autenticarse, accede al layout principal con sidebar de navegacion.
4. Cada pagina se comunica con el backend via peticiones HTTP a `/api/...`.
5. En desarrollo, Vite actua como proxy redirigiendo `/api` a `http://127.0.0.1:9999`.
6. En produccion, CloudFront redirige `/api/*` al API Gateway y el resto al S3.

### Configuracion del proxy (vite.config.js)

```javascript
server: {
    port: 5500,
    proxy: {
      "/api": "http://127.0.0.1:9999",
    },
}
```

Todas las llamadas del frontend pasan por un unico cliente centralizado (`api/client.js`) que usa `API_BASE = import.meta.env.VITE_API_URL || "/api"`.

### Paginas de la aplicacion

| Pagina | Ruta | Roles | Que hace |
|--------|------|-------|---------|
| `LoginPage` | `/login` | — | Autenticacion (split-screen) |
| `PacientesPage` | `/pacientes/alta` | admin, prescriptor | Alta clinica de pacientes |
| `HistorialPacientesPage` | `/pacientes/historial` | admin, prescriptor | Historial de pacientes con filtros |
| `PrescripcionPage` | `/prescripciones/alta` | todos | Alta de prescripcion oncologica con validacion |
| `HistorialPrescripcionesPage` | `/prescripciones/historial` | todos | Historial de prescripciones |
| `AcuerdoPage` | `/acuerdos` | admin | Gestion de acuerdos con laboratorios |
| `EmpadronamientoPage` | `/empadronamientos/:tipo` | admin | Alta de empadronamientos (Tipo A, B) |
| `HistorialEmpadronamientosPage` | `/empadronamientos/historial` | admin | Historial de empadronamientos |
| `AuditQueuePage` | `/auditoria/cola` | auditor, admin | Cola de casos pendientes de revision |
| `AuditCasePage` | `/auditoria/caso/:id` | auditor, admin | Detalle de caso con dictamen y correcciones |
| `TrazabilidadPage` | `/trazabilidad` | auditor, admin | Bloques del ledger y verificacion de integridad |
| `AltaMedicamentosPage` | `/medicamentos/alta` | admin | Alta de medicamentos |
| `HistorialMedicamentosPage` | `/medicamentos/historial` | admin | Historial de medicamentos |
| `MonodrogasPage` | `/monodrogas/alta` | admin | Alta de monodrogas |
| `HistorialMonodrogasPage` | `/monodrogas/historial` | admin | Historial de monodrogas |

### Autenticacion y autorizacion (RBAC)

Todas las rutas (excepto `/login`) estan protegidas por `ProtectedRoute`, que verifica la existencia de un token valido antes de renderizar el contenido. Cada ruta puede especificar un array de roles permitidos; si el usuario no tiene el rol requerido, se muestra "Acceso denegado".

El sidebar de navegacion filtra automaticamente los menus segun el rol del usuario autenticado.

| Rol | Modulos accesibles |
|-----|-------------------|
| `administrador` | Todos los modulos |
| `prescriptor` | Pacientes, prescripciones |
| `auditor` | Cola de auditoria, trazabilidad |

### Como levantar el frontend (desarrollo local)

```bash
cd frontend
npm install
npm run dev
```

La app queda disponible en `http://localhost:5500`.

---

## 4. Backend (Python + FastAPI)

### Que es

El backend es el **servidor** que recibe peticiones del frontend, ejecuta la logica de negocio y devuelve respuestas JSON.

| Tecnologia | Para que sirve |
|-----------|---------------|
| **Python 3.12** | Lenguaje de programacion |
| **FastAPI** | Framework web para APIs REST |
| **Uvicorn** | Servidor ASGI |
| **Pydantic** | Validacion automatica de datos |
| **psycopg2** | Driver PostgreSQL (pool de conexiones) |
| **python-dotenv** | Carga de variables de entorno desde `.env` |
| **Pandas / Openpyxl** | Importacion de datos desde Excel |

### Arquitectura del backend (capas)

```
Peticion HTTP
     |
     v
+-----------+     +----------------+     +-----------+     +--------------+
|  Router   |---->| Auth Middleware |---->|  Service  |---->|  Repository  |
| (/api/*)  |     | (RBAC)         |     | (Logica)  |     | (PG / Mem)   |
+-----------+     +----------------+     +-----------+     +--------------+
                                              |                   |
                                              v                   v
                                        +----------+       +----------+
                                        |  Ledger  |       | db.py    |
                                        | Service  |       | (Pool)   |
                                        | (SHA-256)|       +----------+
                                        +----------+            |
                                                                v
                                                          +----------+
                                                          | sql/*.sql|
                                                          | (Queries)|
                                                          +----------+
```

| Capa | Archivo ejemplo | Que hace |
|------|----------------|---------|
| **Router** | `prescription_router.py` | Define los endpoints HTTP. Recibe datos del frontend. |
| **Auth Middleware** | `auth_middleware.py` | Extrae token, valida usuario, verifica rol (RBAC). |
| **Service** | `prescription_service.py` | Logica de negocio: valida la prescripcion, calcula superficie corporal, registra en el ledger, crea caso de auditoria si estado es REVISION. |
| **Audit** | `audit_service.py` | Gestiona cola de auditoria, dictamenes y correcciones con registro en ledger. |
| **Validation** | `validation_service.py` | Motor de reglas stub que evalua completitud y consistencia del estadio/metastasis. |
| **Ledger** | `ledger_service.py` | Cadena de bloques en memoria: cada operacion se registra como un bloque con hash SHA-256. |
| **Repository** | `prescription_repo.py` | Soporte dual: PostgreSQL (via sql/*.sql) o almacenamiento en memoria. |
| **DB** | `db.py` | Pool de conexiones PostgreSQL (`SimpleConnectionPool`), context manager, fallback automatico si `DATABASE_URL` no esta definida. |
| **Model** | `prescription.py` | Define la forma de los datos con Pydantic. |

### Endpoints principales

Todos los endpoints de negocio estan bajo el prefijo `/api`. Los endpoints protegidos requieren header `Authorization: Bearer <token>`.

| Metodo | Ruta | Rol | Descripcion |
|--------|------|-----|-------------|
| `GET`  | `/` | — | Health check (usado por ECS) |
| `POST` | `/api/auth/login` | — | Iniciar sesion |
| `GET`  | `/api/auth/me` | cualquiera | Usuario actual |
| `POST` | `/api/patients` | admin, prescriptor | Crear paciente |
| `GET`  | `/api/patients` | cualquiera | Listar pacientes |
| `POST` | `/api/prescriptions` | admin, prescriptor | Crear prescripcion (valida + ledger + caso auditoria) |
| `GET`  | `/api/prescriptions` | cualquiera | Listar prescripciones |
| `POST` | `/api/agreements` | admin | Crear acuerdo |
| `GET`  | `/api/agreements` | cualquiera | Listar acuerdos |
| `POST` | `/api/enrollments` | admin | Crear empadronamiento |
| `GET`  | `/api/enrollments` | cualquiera | Listar empadronamientos |
| `GET`  | `/api/audit/queue` | auditor, admin | Cola de auditoria |
| `GET`  | `/api/audit/cases/{id}` | auditor, admin | Detalle de caso |
| `POST` | `/api/audit/cases/{id}/dictamen` | auditor, admin | Emitir dictamen |
| `POST` | `/api/audit/cases/{id}/corrections` | auditor, admin | Registrar correccion |
| `GET`  | `/api/audit/cases/{id}/history` | auditor, admin | Historial de correcciones |
| `GET`  | `/api/ledger` | cualquiera | Bloques del ledger |
| `GET`  | `/api/ledger/verify` | cualquiera | Verificar integridad de la cadena |
| `POST` | `/api/medications` | admin | Crear medicamento |
| `POST` | `/api/monodrugs` | admin | Crear monodroga |

### Motor de validacion (ValidationService)

El motor de validacion es un **stub** que aplica reglas basicas como placeholder del motor hibrido (reglas + ML) descrito en la tesis:

| Regla | Resultado si falla |
|-------|--------------------|
| Campos obligatorios vacios (CIE-10, esquema, linea) | RECHAZADO |
| Estadio IV sin metastasis M1 | RECHAZADO |
| Estadio localizado (I/II/III) con metastasis M1 | RECHAZADO |
| Dosis <= 0 | RECHAZADO |
| Todo correcto | REVISION (se deriva a revision humana) |

El motor nunca aprueba automaticamente (criterio recall-first): siempre deriva a REVISION si no hay errores evidentes.

### Como levantar el backend (desarrollo local)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m backend.main
```

La API queda en `http://127.0.0.1:9999`. Swagger en `http://127.0.0.1:9999/docs`.

---

## 5. Prescripciones on-chain (fuente de verdad en Fabric)

### Que es

Las prescripciones **no se guardan en la RDS**: por contener datos clinicos sensibles, su unica fuente de verdad es el world state de Hyperledger Fabric. El ledger interno SHA-256 que existia en el backend fue retirado por completo; la trazabilidad ahora usa transacciones Fabric reales.

### Como funciona el alta (sincrona, dentro del request)

1. El **prescriptor** completa el checklist clinico; el backend deriva la superficie corporal (Mosteller) y las dosis por defecto.
2. El **motor hibrido reglas + ML** emite su veredicto (APROBADO / RECHAZADO / REVISION) como soporte de decision.
3. El backend genera un **ULID** como ID, arma el **payload canonico** `{clinical, created_at, ml}` y calcula su SHA-256 (`payload_hash`).
4. Invoca `CreatePrescription` via el puente **fabric-gateway-svc**, firmando con la identidad de **PrescriptorMSP**. Las tres organizaciones endosan (politica AND) y la transaccion se commitea.
5. El asset nace en estado **PENDIENTE_AUDITORIA**. Si la red no responde, el alta falla con 503: no hay copia off-chain ni cola de reintentos.

### Ciclo de auditoria on-chain

```
PENDIENTE_AUDITORIA ──revision──> EN_REVISION ──aprobar/rechazar──> APROBADA | RECHAZADA
        └───────────────aprobar/rechazar (dictamen directo)──────────────┘
```

Cada accion del auditor (firmada como **MedChainMSP**) valida la transicion en el chaincode y encadena un nuevo hash: `event_hash = SHA256(prev_hash | accion | estado | auditor | SHA256(justificacion) | timestamp)`. La convencion completa y verificable esta en [docs/HASHING.md](docs/HASHING.md).

### Verificacion de integridad

`GET /api/prescriptions/{id}/verify` re-canonicaliza el contenido del asset, recomputa `payload_hash` y recorre la cadena de eventos verificando cada eslabon. Cualquier adulteracion del contenido clinico o de un dictamen rompe la cadena y se detecta.

---

## 6. Blockchain privada (Hyperledger Fabric en EC2)

### Que es una blockchain privada

| Caracteristica | Publica (ej: Ethereum) | Privada (ej: Hyperledger Fabric) |
|---------------|----------------------|--------------------------------|
| Quien participa | Cualquiera | Solo miembros autorizados |
| Transparencia | Todo es publico | Solo los miembros ven los datos |
| Velocidad | Lenta (miles de nodos) | Rapida (pocos nodos controlados) |
| Costo por transaccion | Gas (caro) | Sin costos de gas |
| Uso tipico | Criptomonedas, NFTs | Salud, supply chain, auditoria |

Para este proyecto usamos **Hyperledger Fabric 2.5 LTS** porque es una blockchain **privada/permisionada**: solo nuestros servidores autorizados pueden leer y escribir datos.

### Arquitectura de la red

La red corre en una **instancia EC2 t3.large** dedicada con Docker Compose. Tres organizaciones con semantica de negocio monitorean el ciclo de vida de cada prescripcion:

```
EC2 (t3.large, Ubuntu 24.04, Elastic IP: 34.199.204.55)
|
|-- Docker Compose
|   |-- peer0.prescriptor.medchain.com   PrescriptorMSP (centro prescriptor)  + couchdb.prescriptor
|   |-- peer0.auditoria.medchain.com     MedChainMSP (empresa auditora)       + couchdb.auditoria
|   |-- peer0.prepaga.medchain.com       PrepagaMSP (financiador/prepaga)     + couchdb.prepaga
|   |-- orderer.medchain.com             Servicio de ordenamiento (Raft/etcdraft)
|   |-- fabric-gateway                   Puente HTTP -> Fabric Gateway SDK (puerto 8081)
|   |-- cli                              Herramientas de administracion
|
|-- Canal: mychannel
|-- Chaincode: prescriptions (chaincode/prescription-contract)
|-- Endorsement: AND('PrescriptorMSP.peer','MedChainMSP.peer','PrepagaMSP.peer')
```

| Componente | Que es | Version |
|-----------|--------|---------|
| **Hyperledger Fabric** | Framework de blockchain permisionada | 2.5.15 LTS |
| **Orderer** | Ordena transacciones en bloques (consenso Raft) | etcdraft |
| **Peers** | 3 nodos (Prescriptor, MedChain, Prepaga) con copia del ledger | Fabric 2.5 |
| **CouchDB** | State DB por peer (habilita rich queries con paginacion) | 3.3 |
| **fabric-gateway-svc** | Puente HTTP del backend, una identidad X509 por organizacion | Go + fabric-gateway 1.11 |
| **Chaincode** | Smart contract en Go | Go 1.21+ |
| **Channel Participation API** | Gestion de canales sin system channel | Nativa |

**Politica de endorsement AND**: ninguna escritura entra al ledger sin la firma de las tres organizaciones — esa es la garantia de no adulteracion. La contracara (limitacion aceptada para la tesis) es que si un peer esta caido, las escrituras se bloquean; el estado de cada peer es visible en la pantalla "Salud del sistema".

### Como levantar la red

```bash
ssh -i mi-key.pem ubuntu@34.199.204.55

cd ~/PFI-Proyecto-Final/fabric
cp network/.env.example network/.env   # 1 sola vez: ajustar GATEWAY_AUTH_TOKEN
./network.sh install        # Binarios + imagenes Docker (1 sola vez)
./network.sh up             # Genera cripto (3 orgs) + levanta contenedores
./network.sh createChannel  # Crea mychannel y une los 3 peers
./network.sh deployCC       # Despliega `prescriptions` con la politica AND

./network.sh down           # Apaga y limpia todo
```

Documentacion detallada: [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md)

---

## 7. Chaincode (Smart Contract en Go)

### Que es

El chaincode es un programa que vive dentro de la blockchain y define que datos se pueden guardar, que operaciones se pueden hacer y que reglas de validacion existen.

### Estructura (chaincode/prescription-contract/contract.go)

El `PrescriptionContract` administra el ciclo de vida completo de las prescripciones. Funciones:

#### CreatePrescription — solo PrescriptorMSP

```go
func (pc *PrescriptionContract) CreatePrescription(ctx, prescriptionID, canonicalJSON) (string, error)
```

1. Verifica que la firma sea de `PrescriptorMSP` (control de acceso por MSP).
2. Verifica que la clave `PRESC_<ULID>` no exista (idempotencia: un reintento con el mismo ID es seguro).
3. Hashea el **string exacto** del payload canonico recibido -> `payload_hash`.
4. Crea el asset en estado `PENDIENTE_AUDITORIA` con `current_hash = payload_hash`.

#### AuditPrescription — solo MedChainMSP

```go
func (pc *PrescriptionContract) AuditPrescription(ctx, prescriptionID, accion, justificacion, auditor) (string, error)
```

1. Verifica la firma de `MedChainMSP` y mapea la accion (`revision`/`aprobar`/`rechazar`) al estado resultante.
2. **Valida la transicion de estado on-chain** (la maquina de estados vive en el contrato, no en el backend).
3. Encadena `event_hash` sobre `current_hash` usando el timestamp de la transaccion (`GetTxTimestamp()`, deterministico para los 3 endorsers — nunca `time.Now()`).
4. Appendea el evento a `audit_events` y actualiza `estado` y `current_hash`.

#### Lecturas — las tres organizaciones

- `GetPrescription(id)` — detalle del asset.
- `ListPrescriptions(pageSize, bookmark)` — listado general, mas recientes primero.
- `QueryPrescriptionsByEstado(estado, pageSize, bookmark)` — la cola de auditoria (FIFO).
- `QueryPrescriptionsByPatient(patientID, pageSize, bookmark)` — historial por paciente (seudonimo).
- `GetPrescriptionHistory(id)` — todas las versiones del asset con sus `tx_id` reales.

Las rich queries usan CouchDB con indices declarados en `META-INF/statedb/couchdb/indexes/` y paginacion por bookmark.

### El asset en blockchain (sin PHI)

```go
type PrescriptionAsset struct {
    DocType          string          // "prescription"
    PrescriptionID   string          // ULID generado por el backend
    PrescriptionCode string          // "PRESC-<ULID>"
    Estado           string          // PENDIENTE_AUDITORIA | EN_REVISION | APROBADA | RECHAZADA
    Clinical         json.RawMessage // payload clinico completo (patient_id seudonimo, sin nombre/PHI)
    ML               json.RawMessage // veredicto del motor reglas + ML (soporte de decision)
    CreatedAt        string
    CreatedByMSP     string          // PrescriptorMSP
    PayloadHash      string          // SHA-256 del payload canonico
    CurrentHash      string          // ultimo eslabon de la cadena de auditoria
    AuditEvents      []AuditEvent    // dictamenes encadenados por hash
}
```

`Clinical` y `ML` se almacenan como JSON crudo, byte a byte igual al payload canonico: cualquiera de las tres organizaciones puede recomputar `payload_hash` y detectar adulteraciones (ver [docs/HASHING.md](docs/HASHING.md)). Los tests del contrato (`contract_test.go`) verifican la maquina de estados, el control por MSP y los vectores de hash compartidos con Python.

---

## 8. Despliegue en AWS

### Diagrama de servicios

```
                   +---------------------------------------------+
                   |              CloudFront (HTTPS)              |
                   |         d3qe3o25c33oqd.cloudfront.net        |
                   +-----+----------------------------+----------+
                         |                            |
                    /*  (default)                /api/*
                         |                            |
                   +-----+-----+            +---------+---------+
                   |    S3     |            | API Gateway       |
                   | Bucket    |            | HTTP API          |
                   | (React    |            | vl5nsf5jt5        |
                   |  build)   |            +--------+----------+
                   +-----------+                     |
                                                VPC Link
                                                     |
                                         +-----------+-----------+
                                         |     VPC (10.0.0.0/16) |
                                         |                       |
                                         |  +------------------+ |
                                         |  | ECS Fargate      | |
                                         |  | medchain-cluster | |
                                         |  | Puerto 8000      | |
                                         |  | FastAPI/Uvicorn  | |
                                         |  +------------------+ |
                                         |                       |
                                         |  Cloud Map (discovery)|
                                         +-----------------------+

            +---------------------------+
            |   EC2 separada            |
            |   pfi-fabric              |
            |   34.199.204.55           |
            |   Hyperledger Fabric      |
            +---------------------------+
```

### Servicios y sus roles

| Servicio | Que hace | Costo estimado |
|----------|---------|----------------|
| **S3** | Almacena los archivos estaticos del frontend (HTML, JS, CSS) | ~$0.02/mes |
| **CloudFront** | CDN global con HTTPS. Distribuye el frontend y rutea `/api/*` al backend | ~$1/mes (bajo trafico) |
| **ECR** | Registro de imagenes Docker del backend | ~$0.10/mes |
| **ECS Fargate** | Ejecuta el contenedor del backend sin gestionar servidores | ~$15/mes (0.25 vCPU, 512 MB) |
| **API Gateway HTTP API** | Expone el backend a internet via VPC Link (sin ALB) | ~$1/mes |
| **Secrets Manager** | Almacena credenciales de autenticacion (AUTH_USERNAME, etc.) | ~$1.20/mes |
| **Cloud Map** | Service discovery para que API Gateway encuentre el contenedor ECS | ~$0.10/mes |
| **EC2 t3.large** | Blockchain Fabric con Docker (2 vCPU, 8 GB RAM, 30 GB disco) | ~$60/mes encendida, ~$2.4/mes apagada |

### URLs de produccion

| Recurso | URL |
|---------|-----|
| App (usuario final) | `https://d3qe3o25c33oqd.cloudfront.net` |
| API Gateway (directo) | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com` |
| Health check | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/` |
| Swagger | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/docs` |

### Guias de despliegue

- **Paso a paso por consola web:** [docs/05-deploy-aws-consola.md](docs/05-deploy-aws-consola.md)
- **Scripts automatizados (CLI):** carpeta `deploy/`
- **Blockchain en EC2:** [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md)

### Como se despliega el backend (manual)

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 007072540405.dkr.ecr.us-east-1.amazonaws.com
docker build -t medchain-backend .
docker tag medchain-backend:latest 007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
docker push 007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
aws ecs update-service --cluster medchain-cluster --service medchain-backend-svc --force-new-deployment --region us-east-1
```

### Como se despliega el frontend (manual)

```bash
cd frontend
npm run build
aws s3 sync dist/ s3://medchain-frontend-007072540405-007072540405-us-east-1-an/ --delete
aws cloudfront create-invalidation --distribution-id E3UXMQZNKANQDB --paths "/*"
```

---

## 9. CI/CD con GitHub Actions

### Que es

Un pipeline de integracion y despliegue continuo que **automaticamente** construye y despliega la aplicacion cada vez que se pushea a la rama `main`. Un push a `desarrollo` corre solo el CI (tests y lint).

### Como funciona

```
Push a rama "main"
         |
         v
GitHub Actions detecta que archivos cambiaron
         |
         +------ backend/** o Dockerfile o requirements.txt cambiaron?
         |       SI --> Job: Deploy Backend
         |              1. Login a ECR
         |              2. Docker build + push
         |              3. ECS update-service --force-new-deployment
         |
         +------ frontend/** cambio?
         |       SI --> Job: Deploy Frontend
         |              1. npm install + build
         |              2. aws s3 sync
         |              3. CloudFront invalidation
         |
         +------ blockchain/** o fabric/** cambio?
                 SI --> Job: Deploy Blockchain
                        1. Enciende la EC2 si esta apagada
                        2. Abre SSH temporalmente en el Security Group
                        3. SSH: git pull + redeploy chaincode
                        4. Cierra SSH del Security Group
```

Los tres jobs corren **en paralelo** si hay cambios en multiples componentes.

### Archivo de configuracion

El workflow esta en `.github/workflows/deploy.yml`.

### Secrets necesarios en GitHub

Configurar una sola vez en **GitHub > Settings > Secrets and variables > Actions**:

| Secret | Descripcion |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | Access Key del usuario IAM `medchain-admin` |
| `AWS_SECRET_ACCESS_KEY` | Secret Key del mismo usuario |
| `EC2_SSH_KEY` | Contenido del archivo `.pem` para SSH a la EC2 de blockchain |
| `EC2_HOST` | Elastic IP de la EC2 (`34.199.204.55`) |
| `EC2_USER` | Usuario SSH (`ubuntu`) |

### Seguridad del deploy de blockchain

El job de blockchain maneja el acceso SSH de forma segura:
1. Obtiene la IP publica del runner de GitHub Actions.
2. Abre una regla de SSH **solo para esa IP** en el Security Group de la EC2.
3. Ejecuta el despliegue.
4. **Siempre** (incluso si falla) revoca la regla SSH y limpia la clave.

---

## 10. Flujo completo: que pasa cuando se crea una prescripcion

```
1. El prescriptor llena el formulario de prescripcion en el frontend
   (paciente, diagnostico CIE-10, estadio, TNM, esquema, dosis, peso, talla)
                  |
                  v
2. Frontend envia POST /api/prescriptions al backend (rol prescriptor)
                  |
                  v
3. PrescriptionService calcula superficie corporal (Mosteller) y dosis por defecto
                  |
                  v
4. ValidationService (motor hibrido reglas + LightGBM) emite el veredicto:
   - Reglas duras (TNM/estadio, dosis) -> RECHAZADO con motivos atribuibles
   - Modelo ML calibrado con doble umbral -> APROBADO o REVISION
   - RNF-15: el modelo solo NUNCA rechaza sin regla atribuible
                  |
                  v
5. El backend genera un ULID, arma el payload canonico {clinical, created_at, ml}
   y calcula su SHA-256 (payload_hash)
                  |
                  v
6. FabricPrescriptionRepository invoca CreatePrescription via fabric-gateway-svc,
   firmando como PrescriptorMSP. Los peers de las 3 organizaciones endosan
   (politica AND), el orderer commitea y el asset queda en el world state
   en estado PENDIENTE_AUDITORIA
                  |
                  v
7. Frontend muestra el asset registrado: estado on-chain, veredicto ML,
   TxID real de Fabric y payload_hash
   (si la red no responde: error 503, no queda nada a medias)
```

### Flujo de auditoria (post-prescripcion)

```
1. El auditor accede a /auditoria/cola: la cola son los assets en estado
   PENDIENTE_AUDITORIA / EN_REVISION leidos de Fabric (FIFO)
                  |
                  v
2. Abre una prescripcion: ve el bloque clinico completo + el veredicto ML
   como soporte de decision + el historial de transacciones
                  |
                  v
3. Registra una accion (firmada como MedChainMSP):
   - revision  -> la prescripcion queda EN_REVISION (estado informativo)
   - aprobar   -> APROBADA (terminal)
   - rechazar  -> RECHAZADA (terminal)
   El chaincode valida la transicion y encadena un nuevo hash (event_hash)
                  |
                  v
4. Las tres organizaciones ven el mismo estado inmutable; cualquier
   adulteracion rompe la cadena de hashes y es detectable via /verify
```

### Por que este flujo importa

- **Paso 4** (validacion): el ML es soporte de decision con explicabilidad; nunca cierra el ciclo solo.
- **Paso 6** (endorsement AND): ninguna prescripcion entra al ledger sin la firma del prescriptor, la auditora y la prepaga.
- **Paso 3 de auditoria** (dictamen on-chain): el dictamen es inmutable, con auditor, justificacion y hash encadenado.
- **Sin copia off-chain**: no existe una segunda fuente de verdad que pueda divergir o adulterarse.

---

## 11. Integracion backend <-> blockchain (implementada)

El backend llega a la red via **fabric-gateway-svc** (`fabric-gateway-svc/main.go`), un puente HTTP construido sobre el **Fabric Gateway SDK** oficial:

1. Mantiene **una conexion gRPC + identidad X509 por organizacion** (`User1@<org>` generado por cryptogen).
2. El backend indica el `actor` en cada request (`prescriptor` | `auditor` | `prepaga`) y el puente firma con el MSP correspondiente — asi el control de acceso por MSP del chaincode se ejerce de verdad.
3. La autenticacion de entrada es un token compartido (`X-Gateway-Token`, comparacion en tiempo constante); el puerto 8081 solo debe ser accesible desde el SG del backend.
4. Los errores tipados del SDK (endorse/submit/commit) se mapean a HTTP y el backend distingue errores de negocio (409, sin retry) de indisponibilidad (503, con retry + circuit breaker).

Variables en el backend: `FABRIC_GATEWAY_URL` y `GATEWAY_AUTH_TOKEN` (obligatorias en production, fail-fast).

---

## 12. Glosario de terminos

| Termino | Definicion |
|---------|-----------|
| **API** | Interfaz de programacion: URLs que un servidor expone para recibir y enviar datos |
| **API Gateway** | Servicio de AWS que expone APIs HTTP a internet y las conecta a servicios internos |
| **Backend** | Servidor que procesa logica de negocio. Solo recibe y envia datos JSON |
| **Blockchain** | Base de datos distribuida donde los registros son inmutables y auditables |
| **CA (Certificate Authority)** | Autoridad certificadora que emite credenciales digitales |
| **Chaincode** | Smart contract que define reglas de negocio dentro de la blockchain |
| **Channel** | Canal privado dentro de la red Fabric donde se ejecutan transacciones |
| **CI/CD** | Integracion y despliegue continuos: automatiza build, test y deploy |
| **CloudFront** | CDN (Content Delivery Network) de AWS con HTTPS y cache global |
| **Cloud Map** | Service discovery de AWS: permite que API Gateway encuentre contenedores ECS |
| **CORS** | Politica de seguridad del navegador que restringe peticiones entre distintos origenes |
| **Docker** | Herramienta que empaqueta aplicaciones en contenedores aislados |
| **EC2** | Servidores virtuales en la nube de AWS |
| **ECR** | Elastic Container Registry: registro privado de imagenes Docker en AWS |
| **ECS Fargate** | Servicio serverless de AWS que ejecuta contenedores Docker sin gestionar servidores |
| **Endpoint** | Direccion (URL + puerto) donde un servicio esta disponible |
| **FastAPI** | Framework de Python para crear APIs web rapidas con documentacion automatica |
| **Frontend** | Parte visual de la aplicacion: lo que el usuario ve en el navegador |
| **GitHub Actions** | Servicio de CI/CD integrado en GitHub que ejecuta workflows automaticamente |
| **Go (Golang)** | Lenguaje de programacion usado para el chaincode |
| **gRPC** | Protocolo de comunicacion usado internamente por Fabric |
| **Hyperledger Fabric** | Framework de blockchain privada/permisionada (Linux Foundation) |
| **Ledger** | Libro mayor de la blockchain: contiene todos los registros y transacciones |
| **MSP** | Membership Service Provider: certificados que identifican a un miembro de la red |
| **Orderer** | Servicio que ordena transacciones en bloques dentro de la blockchain |
| **Peer** | Nodo que almacena una copia del ledger y ejecuta el chaincode |
| **React** | Libreria de JavaScript para construir interfaces con componentes |
| **S3** | Simple Storage Service: almacenamiento de objetos de AWS |
| **Security Group** | Firewall virtual de AWS que controla trafico entrante y saliente |
| **SHA-256** | Algoritmo de hash criptografico usado para enlazar bloques en la cadena |
| **SPA** | Single Page Application: aplicacion web que carga una sola vez y navega sin recargar |
| **TLS** | Transport Layer Security: protocolo de cifrado para comunicacion segura |
| **Transaction ID (txId)** | Identificador unico de una transaccion en la blockchain |
| **Vite** | Herramienta de desarrollo frontend con recarga en caliente y builds optimizados |
| **VPC** | Virtual Private Cloud: red privada virtual en AWS |
| **VPC Link** | Conexion privada entre API Gateway y recursos dentro de la VPC |

---

## 13. Costos de AWS y como optimizarlos

### Costo mensual estimado (todo encendido)

| Servicio | Costo/mes |
|----------|-----------|
| ECS Fargate (0.25 vCPU, 512 MB) | ~$15 |
| EC2 t3.large (blockchain) | ~$60 |
| API Gateway HTTP API | ~$1 |
| CloudFront | ~$1 |
| Secrets Manager | ~$1.20 |
| S3 + ECR + Cloud Map + CloudWatch | ~$1 |
| **Total (todo encendido)** | **~$80/mes** |

### Como reducir costos

1. **Apagar la EC2 de blockchain** cuando no se use: `Stop instance` desde la consola. El disco persiste (~$2.4/mes) pero el computo no cobra.
2. **ECS no se puede "apagar"** sin eliminar el servicio. Para pausar: poner `desiredCount=0` en el servicio ECS.
3. **CloudFront y S3** son despreciables en bajo trafico.

### Verificar que no haya cargos inesperados

1. **EC2 > Elastic IPs**: Si hay una IP elastica no asociada a instancia, cobra ~$3.6/mes. Liberarla si no se usa.
2. **EC2 > Volumes**: Verificar que no haya discos EBS huerfanos.
3. **CloudWatch > Log Groups**: Eliminar logs viejos si no se necesitan.
4. **AWS Cost Explorer**: Revisar `Billing and Cost Management > Cost Explorer` periodicamente.

### Para eliminar todo

```bash
bash deploy/99-cleanup.sh
```

O seguir la guia manual en [docs/05-deploy-aws-consola.md](docs/05-deploy-aws-consola.md).
