# MedChain AI

Sistema de gestión de empadronamiento de pacientes con registro inmutable en blockchain privada (Hyperledger Fabric).

Proyecto Final de Ingeniería Informática (UADE).

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| **Frontend** | React + Vite (puerto 5500) |
| **Backend** | Python 3.11 + FastAPI (puerto 9999) |
| **Modelo IA** | Python — generación de datos sintéticos para clasificación de diabetes |
| **Blockchain** | Hyperledger Fabric 2.5 LTS (red propia, ver `fabric/`) |
| **Smart Contract** | Go |

## Estructura del proyecto

```
├── backend/                 API REST en Python
│   ├── main.py              Punto de entrada (FastAPI + Uvicorn)
│   ├── db.py                Conexion a PostgreSQL (pool, context manager, fallback en memoria)
│   ├── auth_middleware.py   Middleware de autenticacion y RBAC
│   ├── dependencies.py      Inyeccion de dependencias (singleton repos/services)
│   ├── models/              Modelos Pydantic (patient, prescription, audit, agreement, enrollment, etc.)
│   ├── repositories/        Repositorios con soporte dual PostgreSQL / en memoria
│   ├── routers/             Endpoints de la API con autenticacion y control de roles
│   └── services/            Logica de negocio (validacion, ledger, auditoria)
├── sql/                     Queries SQL externalizadas
│   ├── schema.sql           DDL de todas las tablas (11 tablas)
│   ├── patients.sql         Queries de pacientes
│   ├── prescriptions.sql    Queries de prescripciones
│   ├── audit.sql            Queries de auditoria (casos, dictamenes, correcciones)
│   ├── agreements.sql       Queries de acuerdos
│   ├── enrollments.sql      Queries de empadronamientos
│   ├── medications.sql      Queries de medicamentos
│   ├── monodrugs.sql        Queries de monodrogas
│   ├── ledger.sql           Queries del ledger
│   └── users.sql            Queries de usuarios
├── frontend/                Aplicacion web React
│   ├── src/
│   │   ├── api/             Clientes HTTP al backend (audit, agreements, enrollments, etc.)
│   │   ├── auth/            Contexto de autenticacion y proteccion de rutas con RBAC
│   │   ├── components/      Componentes reutilizables (Layout, Sidebar con menu por roles)
│   │   ├── hooks/           Hooks personalizados
│   │   └── pages/           Paginas de la aplicacion (incluye auditoria)
│   └── vite.config.js       Dev server + proxy al backend
├── ml-models/               Modulo de inteligencia artificial
│   └── datosSinteticos.py   Generacion de datasets sinteticos de diabetes
├── blockchain/              Smart contract PatientContract en Go
│   ├── main.go              CreatePatient, QueryPatient, GetPatientHistory
│   └── go.mod               Dependencias (fabric-contract-api-go)
├── chaincode/               Chaincode de ejemplo desplegado por la red Fabric
│   └── asset-transfer-basic/
├── fabric/                  Infraestructura de la red Hyperledger Fabric
│   ├── network.sh
│   ├── network/             crypto-config, configtx, compose
│   └── scripts/             bootstrap, createChannel, deployChaincode, etc.
├── .github/workflows/       CI/CD con GitHub Actions
│   └── deploy.yml           Deploy automatico a AWS al pushear
├── deploy/                  Scripts de despliegue en AWS
│   ├── deploy-all.sh        Script maestro (ejecuta todo)
│   ├── 00-variables.sh      Variables de configuracion
│   ├── 01-vpc-network.sh    VPC, subredes, Security Groups
│   ├── 02-ecr-push.sh       Build Docker + push a ECR
│   ├── 03-secrets-iam.sh    Secrets Manager + roles IAM
│   ├── 04-ecs-cluster.sh    ECS Fargate + Cloud Map
│   ├── 05-api-gateway.sh    API Gateway HTTP API + VPC Link
│   ├── 06-s3-cloudfront.sh  S3 + CloudFront (SPA + API)
│   └── 99-cleanup.sh        Limpieza de recursos
├── docs/                    Documentacion
│   ├── 01-prerequisitos.md
│   ├── 02-arquitectura.md
│   ├── 03-uso.md
│   ├── 04-aws-ec2-setup.md
│   └── 05-deploy-aws-consola.md  Guia paso a paso para AWS
├── Dockerfile               Imagen Docker del backend
├── .dockerignore             Exclusiones para Docker build
├── requirements.txt         Dependencias de Python
└── ARQUITECTURA PASO A PASO.md   Documentacion detallada de la arquitectura
```

## Instalación y ejecución (app: frontend + backend)

### Requisitos previos

- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL 15+ (opcional; sin BD, el backend usa almacenamiento en memoria)

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
python -m backend.main
```

La API queda disponible en `http://127.0.0.1:9999`.
Todos los endpoints de negocio estan bajo `/api` (ej. `http://127.0.0.1:9999/api/patients`).
Documentacion interactiva (Swagger) en `http://127.0.0.1:9999/docs`.

#### Variables de entorno (`.env`)

| Variable | Descripcion |
|----------|-------------|
| `AUTH_USERNAME` | Usuario de autenticacion (fallback sin BD) |
| `AUTH_PASSWORD` | Contraseña de autenticacion (fallback sin BD) |
| `DATABASE_URL` | URL de conexion PostgreSQL (ej. `postgresql://user:pass@host:5432/medchain`). Si no se define, el backend usa almacenamiento en memoria |
| `CORS_ORIGINS` | Origenes permitidos para CORS (separados por coma) |

#### Persistencia dual

El backend soporta dos modos de persistencia:

- **PostgreSQL**: Si `DATABASE_URL` esta configurada, todos los repositorios usan la base de datos. Las tablas se crean automaticamente al iniciar (`sql/schema.sql`).
- **En memoria**: Si `DATABASE_URL` no esta definida, los datos se almacenan en listas Python y se pierden al reiniciar.

#### Roles y permisos (RBAC)

El sistema soporta tres roles con permisos diferenciados:

| Rol | Acceso |
|-----|--------|
| `administrador` | Acceso completo a todos los modulos |
| `prescriptor` | Pacientes, prescripciones |
| `auditor` | Cola de auditoria, trazabilidad, dictamenes |

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en `http://localhost:5500`.
Vite actúa como proxy, redirigiendo las peticiones API al backend automáticamente.

## API Endpoints principales

Todos los endpoints de negocio estan bajo el prefijo `/api`. Los endpoints protegidos requieren header `Authorization: Bearer <token>`.

| Metodo | Ruta | Rol requerido | Descripcion |
|--------|------|---------------|-------------|
| `GET`  | `/` | — | Health check |
| `POST` | `/api/auth/login` | — | Iniciar sesion |
| `GET`  | `/api/auth/me` | cualquiera | Usuario actual |
| `POST` | `/api/patients` | admin, prescriptor | Crear paciente |
| `GET`  | `/api/patients` | cualquiera | Listar pacientes |
| `POST` | `/api/patients/bulk-import` | admin | Importar pacientes desde Excel |
| `POST` | `/api/medications` | admin | Crear medicamento |
| `GET`  | `/api/medications` | cualquiera | Listar medicamentos |
| `POST` | `/api/monodrugs` | admin | Crear monodroga |
| `GET`  | `/api/monodrugs` | cualquiera | Listar monodrogas |
| `POST` | `/api/prescriptions` | admin, prescriptor | Crear prescripcion |
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
| `GET`  | `/api/ledger/verify` | cualquiera | Verificar integridad |

## Blockchain

### Smart contract del dominio (`blockchain/`)

El chaincode en Go (`blockchain/main.go`) implementa el `PatientContract` y expone tres funciones:

- **CreatePatient** — Registra un paciente de forma inmutable en el ledger.
- **QueryPatient** — Consulta los datos actuales de un paciente.
- **GetPatientHistory** — Devuelve el historial completo de cambios de un paciente.

### Red Hyperledger Fabric (`fabric/`)

La carpeta `fabric/` contiene una red **Hyperledger Fabric 2.5 LTS** reproducible desde cero:

- **2 organizaciones** (`Org1`, `Org2`), cada una con 1 peer.
- **1 orderer** (consenso Raft / etcdraft), usando la *Channel Participation API* (sin system channel).
- **Material criptográfico** generado con `cryptogen`.
- **Chaincode** de ejemplo (`asset-transfer-basic`) escrito en **Go**.
- **Canal** de aplicación: `mychannel`.

#### Quickstart de la red

> **Requisito:** Docker + Docker Compose corriendo.
> - En **AWS EC2** (recomendado, sin fricción): ver [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md).
> - En **Windows** local: **WSL2 + Docker Desktop**, ver [docs/01-prerequisitos.md](docs/01-prerequisitos.md).

```bash
cd fabric

# 1. Descargar binarios de Fabric e imágenes Docker (una sola vez)
./network.sh install

# 2. Levantar la red (genera cripto + arranca contenedores)
./network.sh up

# 3. Crear el canal 'mychannel' y unir los peers
./network.sh createChannel

# 4. Desplegar el chaincode de ejemplo
./network.sh deployCC

# Apagar y limpiar todo
./network.sh down
```

Más detalle en [docs/03-uso.md](docs/03-uso.md).

#### Versiones

| Componente            | Versión    |
|-----------------------|------------|
| Hyperledger Fabric    | 2.5.15 LTS |
| Fabric CA             | 1.5.13     |
| Chaincode (Go)        | Go 1.22+   |
| Docker Engine         | 29.x       |
| Consenso del orderer  | etcdraft   |

#### Notas de compatibilidad

- **Docker Engine v29+**: requiere Fabric >= 2.5.15 (fix para broken pipe en chaincode build, ver [issue #5350](https://github.com/hyperledger/fabric/issues/5350)).
- **TLS**: los certificados incluyen SANs para `localhost` y `127.0.0.1` para permitir acceso desde el host a los contenedores.
- **go.sum**: debe estar commiteado junto con `go.mod` para que el chaincode compile correctamente dentro de `fabric-ccenv`.
- **configtx.yaml**: las rutas a `organizations/` son relativas a `FABRIC_CFG_PATH` (`fabric/network/`), por lo que usan `./organizations/`.

Para la guía paso a paso de configuración de la blockchain, ver [`ARQUITECTURA PASO A PASO.md`](ARQUITECTURA%20PASO%20A%20PASO.md).

## Despliegue en AWS

La aplicacion esta desplegada en produccion en:

**https://d3qe3o25c33oqd.cloudfront.net**

### Arquitectura en la nube

| Capa | Servicio AWS | Descripcion |
|------|-------------|-------------|
| **Frontend** | S3 + CloudFront | SPA estatica servida con HTTPS |
| **Backend** | ECS Fargate + API Gateway HTTP API | Contenedor Docker serverless |
| **Blockchain** | EC2 dedicada | Red Fabric 2.5 con Docker |

### URLs de produccion

| Recurso | URL |
|---------|-----|
| App (usuario final) | `https://d3qe3o25c33oqd.cloudfront.net` |
| API Gateway (directo) | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com` |
| Health check | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/` |
| Swagger | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/docs` |

### Guias de despliegue

- **Paso a paso por consola web:** [docs/05-deploy-aws-consola.md](docs/05-deploy-aws-consola.md)
- **Scripts automatizados (CLI):** ver carpeta `deploy/`
- **Blockchain en EC2:** [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md)

### Actualizar el frontend en produccion

```bash
cd frontend
npm run build
aws s3 sync dist/ s3://medchain-frontend-007072540405-007072540405-us-east-1-an/ --delete
```

### Actualizar el backend en produccion

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 007072540405.dkr.ecr.us-east-1.amazonaws.com
docker build -t medchain-backend .
docker tag medchain-backend:latest 007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
docker push 007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
aws ecs update-service --cluster medchain-cluster --service medchain-backend-svc --force-new-deployment --region us-east-1
```

### Limpieza de recursos

```bash
bash deploy/99-cleanup.sh
```

### CI/CD (GitHub Actions)

El repositorio tiene un workflow automatico que despliega a AWS cada vez que se pushea a la rama `desarrollo`.

**Que despliega:**
- Si cambia `backend/`, `Dockerfile` o `requirements.txt` -> reconstruye la imagen Docker, la sube a ECR y fuerza un nuevo deploy en ECS Fargate.
- Si cambia `frontend/` -> hace build del frontend, lo sube a S3 e invalida el cache de CloudFront.
- Si cambia `blockchain/` o `fabric/` -> se conecta por SSH a la EC2, hace git pull y redesplega el chaincode con la nueva version.
- Los tres jobs corren en paralelo si hay cambios en multiples componentes.

**Configuracion necesaria (una sola vez):**

Ir a **GitHub > Settings > Secrets and variables > Actions** y crear estos secrets:

| Secret | Valor |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Access Key del usuario IAM `medchain-admin` |
| `AWS_SECRET_ACCESS_KEY` | Secret Key del usuario IAM `medchain-admin` |
| `EC2_SSH_KEY` | Contenido completo del archivo `prueba-blockchain.pem` |
| `EC2_HOST` | `34.199.204.55` (Elastic IP de la EC2 blockchain) |
| `EC2_USER` | `ubuntu` |

El workflow se encuentra en `.github/workflows/deploy.yml`.

## Notas

- Si `DATABASE_URL` esta configurada, los datos persisten en PostgreSQL. Sin ella, se usa almacenamiento en memoria (los datos se pierden al reiniciar).
- El campo `blockchain_tx_id` en los modelos de paciente y dictamen esta preparado para vincular cada registro con su transaccion en blockchain (pendiente de integracion con Hyperledger Fabric).
- La carpeta `ml-models/` contiene los scripts de generacion de datos sinteticos y sera el modulo donde se implementen los modelos de IA del proyecto.
- Los dictamenes y correcciones de auditoria se registran en el ledger inmutable para trazabilidad completa.
