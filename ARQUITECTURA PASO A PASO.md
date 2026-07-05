# Arquitectura Paso a Paso - MedChain AI

## Tabla de contenidos

1. [Vision general del proyecto](#1-vision-general-del-proyecto)
2. [Estructura de carpetas](#2-estructura-de-carpetas)
3. [Frontend (React + Vite)](#3-frontend-react--vite)
4. [Backend (Python + FastAPI)](#4-backend-python--fastapi)
5. [Ledger simulado (blockchain en memoria)](#5-ledger-simulado-blockchain-en-memoria)
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

MedChain AI es una aplicacion web para la **auditoria de prescripciones oncologicas de alta complejidad**. Cada prescripcion pasa por un motor de validacion (stub preliminar, con vision a incorporar reglas + ML) y se registra en un **ledger inmutable** que garantiza trazabilidad completa.

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
|   |-- deploy.yml           Deploy automatico a AWS al pushear a desarrollo
|
|-- backend/                  Servidor API en Python
|   |-- main.py               Punto de entrada (FastAPI + Uvicorn, version 0.5.0)
|   |-- dependencies.py       Inyeccion de dependencias
|   |-- models/               Modelos Pydantic (patient, prescription, ledger, etc.)
|   |-- repositories/         Almacenamiento en memoria
|   |-- routers/              Endpoints bajo /api
|   |   |-- auth_router.py       Autenticacion (login, me, logout)
|   |   |-- patient_router.py    CRUD de pacientes
|   |   |-- prescription_router.py  Prescripciones oncologicas
|   |   |-- ledger_router.py     Bloques del ledger y verificacion
|   |   |-- enrollment_router.py Empadronamientos
|   |   |-- medication_router.py Medicamentos
|   |   |-- monodrug_router.py   Monodrogas
|   |   |-- agreement_router.py  Acuerdos
|   |-- services/             Logica de negocio
|       |-- auth_service.py      Autenticacion con tokens en memoria
|       |-- prescription_service.py  Validacion + registro en ledger
|       |-- validation_service.py    Motor de reglas (stub)
|       |-- ledger_service.py       Cadena de bloques SHA-256
|       |-- patient_service.py
|       |-- enrollment_service.py
|       |-- medication_service.py
|       |-- monodrug_service.py
|       |-- agreement_service.py
|       |-- excel_import_service.py
|
|-- frontend/                 Aplicacion web React
|   |-- index.html
|   |-- vite.config.js        Dev server + proxy /api al backend
|   |-- package.json
|   |-- src/
|       |-- App.jsx            Rutas de la SPA (react-router-dom)
|       |-- main.jsx           Punto de entrada
|       |-- index.css          Estilos globales
|       |-- api/
|       |   |-- client.js      API_BASE configurable (VITE_API_URL || "/api")
|       |-- auth/
|       |   |-- ProtectedRoute.jsx  Proteccion de rutas autenticadas
|       |-- components/        Componentes reutilizables (Layout, FormField, etc.)
|       |-- hooks/             Hooks personalizados
|       |-- pages/             15 paginas de la aplicacion
|
|-- blockchain/               Smart Contract en Go
|   |-- main.go               PatientContract (CreatePatient, QueryPatient, GetPatientHistory)
|   |-- go.mod                Dependencias (fabric-contract-api-go)
|
|-- fabric/                   Infraestructura de la red Hyperledger Fabric
|   |-- network.sh            Punto de entrada (install, up, createChannel, deployCC, down)
|   |-- network/              crypto-config, configtx, compose, .env
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
|-- ml-models/                Modulo de inteligencia artificial
|   |-- datosSinteticos.py    Generacion de datasets sinteticos
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

| Pagina | Ruta | Que hace |
|--------|------|---------|
| `LoginPage` | `/login` | Autenticacion (split-screen) |
| `PacientesPage` | `/pacientes/alta` | Alta clinica de pacientes |
| `HistorialPacientesPage` | `/pacientes/historial` | Historial de pacientes con filtros |
| `PrescripcionPage` | `/prescripciones/alta` | Alta de prescripcion oncologica con validacion |
| `HistorialPrescripcionesPage` | `/prescripciones/historial` | Historial de prescripciones |
| `TrazabilidadPage` | `/trazabilidad` | Bloques del ledger y verificacion de integridad |
| `AltaMedicamentosPage` | `/medicamentos/alta` | Alta de medicamentos |
| `HistorialMedicamentosPage` | `/medicamentos/historial` | Historial de medicamentos |
| `MonodrogasPage` | `/monodrogas/alta` | Alta de monodrogas |
| `HistorialMonodrogasPage` | `/monodrogas/historial` | Historial de monodrogas |
| `AcuerdoPage` | `/acuerdos` | Gestion de acuerdos |
| `EmpadronamientoPage` | `/empadronamientos/:tipo` | Empadronamiento por tipo (A, B) |
| `HistorialEmpadronamientosPage` | `/empadronamientos/historial` | Historial de empadronamientos |

### Autenticacion

Todas las rutas (excepto `/login`) estan protegidas por `ProtectedRoute`, que verifica la existencia de un token valido antes de renderizar el contenido.

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
| **python-dotenv** | Carga de variables de entorno desde `.env` |
| **Pandas / Openpyxl** | Importacion de datos desde Excel |

### Arquitectura del backend (capas)

```
Peticion HTTP
     |
     v
+-----------+     +-----------+     +--------------+
|  Router   |---->|  Service  |---->|  Repository  |
| (/api/*)  |     | (Logica)  |     | (Datos)      |
+-----------+     +-----------+     +--------------+
                       |
                       v
                 +-------------+
                 |   Ledger    |
                 |  Service    |
                 | (SHA-256)   |
                 +-------------+
```

| Capa | Archivo ejemplo | Que hace |
|------|----------------|---------|
| **Router** | `prescription_router.py` | Define los endpoints HTTP. Recibe datos del frontend. |
| **Service** | `prescription_service.py` | Logica de negocio: valida la prescripcion, calcula superficie corporal, registra en el ledger. |
| **Validation** | `validation_service.py` | Motor de reglas stub que evalua completitud y consistencia del estadio/metastasis. |
| **Ledger** | `ledger_service.py` | Cadena de bloques en memoria: cada operacion se registra como un bloque con hash SHA-256. |
| **Repository** | `prescription_repo.py` | Almacenamiento en memoria (los datos se pierden al reiniciar). |
| **Model** | `prescription.py` | Define la forma de los datos con Pydantic. |

### Endpoints principales

Todos los endpoints de negocio estan bajo el prefijo `/api`:

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET`  | `/` | Health check (usado por ECS) |
| `POST` | `/api/auth/login` | Iniciar sesion |
| `GET`  | `/api/auth/me` | Usuario actual |
| `POST` | `/api/patients` | Crear paciente |
| `GET`  | `/api/patients` | Listar pacientes |
| `POST` | `/api/prescriptions` | Crear prescripcion (valida + registra en ledger) |
| `GET`  | `/api/prescriptions` | Listar prescripciones |
| `GET`  | `/api/ledger` | Bloques del ledger |
| `GET`  | `/api/ledger/verify` | Verificar integridad de la cadena |
| `POST` | `/api/enrollments/{tipo}` | Crear empadronamiento |
| `POST` | `/api/medications` | Crear medicamento |
| `POST` | `/api/monodrugs` | Crear monodroga |
| `POST` | `/api/agreements` | Crear acuerdo |

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

## 5. Ledger simulado (blockchain en memoria)

### Que es

El `LedgerService` implementa una **cadena de bloques simulada** dentro del backend. Cada operacion critica (prescripcion, alta de paciente, etc.) genera un nuevo bloque enlazado al anterior mediante hashes SHA-256.

### Como funciona

```
Bloque 0 (Genesis)          Bloque 1                    Bloque 2
+------------------+        +------------------+        +------------------+
| index: 0         |        | index: 1         |        | index: 2         |
| tx_type: genesis |        | tx_type: presc.  |        | tx_type: presc.  |
| payload: {}      |        | payload: {...}   |        | payload: {...}   |
| prev_hash: 000...|        | prev_hash: a3f...|        | prev_hash: 7b2...|
| hash: a3f...     |------->| hash: 7b2...     |------->| hash: e91...     |
+------------------+        +------------------+        +------------------+
```

1. Al iniciar el backend, se crea un **bloque genesis** (indice 0, payload vacio).
2. Cada vez que se crea una prescripcion, el `PrescriptionService` llama a `ledger_service.append()`.
3. El ledger calcula el hash SHA-256 del contenido (indice + timestamp + tipo + payload + hash anterior).
4. El nuevo bloque se agrega a la cadena y su hash se guarda en la prescripcion como `blockchain_tx_id`.

### Verificacion de integridad

El endpoint `GET /api/ledger/verify` recorre toda la cadena recalculando cada hash y verificando que coincida con el almacenado y que el `prev_hash` enlace correctamente con el bloque anterior. Si alguno falla, indica en que bloque se rompio.

### Por que un ledger simulado

La blockchain real (Hyperledger Fabric) corre en una EC2 separada y aun no esta integrada con el backend. El ledger simulado permite:
- Demostrar el concepto de trazabilidad inmutable.
- Que la pagina de Trazabilidad funcione mostrando bloques reales con hashes.
- Facilitar la futura integracion: cuando se conecte Fabric, el `blockchain_tx_id` apuntara a la transaccion real en el ledger distribuido.

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

La red corre en una **instancia EC2 t3.large** dedicada con Docker Compose:

```
EC2 (t3.large, Ubuntu 24.04, Elastic IP: 34.199.204.55)
|
|-- Docker Compose
|   |-- peer0.org1         Nodo par de la Organizacion 1
|   |-- peer0.org2         Nodo par de la Organizacion 2
|   |-- orderer            Servicio de ordenamiento (Raft/etcdraft)
|   |-- cli                Herramientas de administracion
|
|-- Canal: mychannel
|-- Chaincode: asset-transfer-basic (ejemplo) + PatientContract (dominio)
```

| Componente | Que es | Version |
|-----------|--------|---------|
| **Hyperledger Fabric** | Framework de blockchain permisionada | 2.5.15 LTS |
| **Fabric CA** | Autoridad certificadora | 1.5.13 |
| **Orderer** | Ordena transacciones en bloques (consenso Raft) | etcdraft |
| **Peers** | 2 nodos (Org1, Org2) con copia del ledger | Fabric 2.5 |
| **Chaincode** | Smart contract en Go | Go 1.22+ |
| **Channel Participation API** | Gestion de canales sin system channel | Nativa |

### Como levantar la red

```bash
ssh -i mi-key.pem ubuntu@34.199.204.55

cd ~/PFI-Proyecto-Final/fabric
./network.sh install        # Binarios + imagenes Docker (1 sola vez)
./network.sh up             # Genera cripto + levanta contenedores
./network.sh createChannel  # Crea mychannel y une los peers
./network.sh deployCC       # Despliega el chaincode

./network.sh down           # Apaga y limpia todo
```

Documentacion detallada: [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md)

---

## 7. Chaincode (Smart Contract en Go)

### Que es

El chaincode es un programa que vive dentro de la blockchain y define que datos se pueden guardar, que operaciones se pueden hacer y que reglas de validacion existen.

### Estructura (blockchain/main.go)

El archivo define tres funciones en el `PatientContract`:

#### CreatePatient

```go
func (pc *PatientContract) CreatePatient(ctx, patientID, dataJSON) (string, error)
```

1. Recibe un `patientID` y un JSON con datos del paciente.
2. Verifica que no exista un paciente con ese ID (evita duplicados).
3. Agrega metadatos (tipo de documento, timestamp UTC).
4. Guarda el paciente en el ledger distribuido.
5. Devuelve el paciente creado como JSON.

#### QueryPatient

```go
func (pc *PatientContract) QueryPatient(ctx, patientID) (string, error)
```

Busca un paciente por ID en el ledger y devuelve sus datos.

#### GetPatientHistory

```go
func (pc *PatientContract) GetPatientHistory(ctx, patientID) (string, error)
```

Devuelve **todas las versiones** del registro de un paciente (historial completo de cambios), incluyendo `txId`, `timestamp`, `isDelete` y `value` de cada version.

### Datos del paciente en blockchain

```go
type Patient struct {
    DocType              string  // Siempre "patient"
    PatientID            string  // ID unico
    SapID                string  // ID externo del paciente
    FirstName            string
    LastName             string
    BirthDate            string
    Gender               string
    TipoEmpadronamiento string
    FechaInicio          string
    DataHash             string  // Hash de los datos para verificacion
    CreatedAt            string  // Timestamp de creacion en blockchain
}
```

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

Un pipeline de integracion y despliegue continuo que **automaticamente** construye y despliega la aplicacion cada vez que se pushea a la rama `desarrollo`.

### Como funciona

```
Push a rama "desarrollo"
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
1. Usuario llena el formulario de prescripcion en el frontend
   (paciente, diagnostico CIE-10, estadio, TNM, esquema, dosis, peso, talla)
                  |
                  v
2. Frontend envia POST /api/prescriptions al backend
                  |
                  v
3. PrescriptionService recibe los datos
                  |
                  v
4. ValidationService evalua la prescripcion:
   - Verifica campos obligatorios (CIE-10, esquema, linea)
   - Valida consistencia estadio/metastasis (ej: IV sin M1 = RECHAZADO)
   - Valida dosis > 0
   - Si todo OK -> REVISION (deriva a revision humana)
   - Si hay error -> RECHAZADO con motivos
                  |
                  v
5. PrescriptionService calcula superficie corporal (formula de Mosteller)
   BSA = sqrt(talla_cm * peso_kg / 3600)
                  |
                  v
6. LedgerService registra la operacion como un nuevo bloque:
   - Calcula hash SHA-256 (indice + timestamp + tipo + payload + hash anterior)
   - Encadena con el bloque previo
   - Devuelve el bloque con su hash
                  |
                  v
7. Se crea la Prescription con:
   - prescription_code: PRESC-0001
   - validacion: { estado: "REVISION", motivos: [...] }
   - blockchain_tx_id: hash del bloque del ledger
   - block_index: indice del bloque en la cadena
                  |
                  v
8. Se guarda en el PrescriptionRepository (memoria)
                  |
                  v
9. Frontend muestra el resultado con el estado de validacion
   y el blockchain_tx_id para referencia de trazabilidad
```

### Por que este flujo importa

- **Paso 4** (validacion): atrapa errores evidentes antes de registrar la prescripcion.
- **Paso 6** (ledger): crea un registro inmutable (la cadena de hashes no se puede alterar sin romper la verificacion).
- **Paso 7** (blockchain_tx_id): vincula cada prescripcion con su bloque, permitiendo auditoria completa desde la pagina de Trazabilidad.

---

## 11. Proximo paso: conectar el backend con la blockchain real

Actualmente el ledger simulado (SHA-256 en memoria) y la red Fabric (EC2) funcionan de forma independiente. El proximo paso es integrarlos.

### Que implica la integracion

1. **Crear `backend/services/blockchain_service.py`** que se comunique con la red Fabric via REST o gRPC.
2. **Modificar `prescription_service.py`** para que ademas de registrar en el ledger local, invoque `CreatePatient` en el chaincode de Fabric.
3. **Guardar el `txId` real** de la blockchain distribuida (no solo el hash local).
4. **Exponer un endpoint en la EC2** que acepte peticiones REST del backend ECS.

### Opciones de conexion

| Opcion | Complejidad | Descripcion |
|--------|------------|-------------|
| **Proxy REST en la EC2** | Baja | Un servicio Express/FastAPI en la EC2 que recibe peticiones y ejecuta comandos `peer chaincode invoke` |
| **Fabric Gateway SDK** | Media | SDK oficial de Fabric (Node.js/Java) corriendo como sidecar o servicio |
| **API Gateway + Lambda** | Media-Alta | Lambda invoca comandos del peer y expone una API REST |

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
