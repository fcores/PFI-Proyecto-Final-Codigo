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
│   ├── models/              Modelos Pydantic (patient, enrollment, etc.)
│   ├── repositories/        Almacenamiento en memoria
│   ├── routers/             Endpoints de la API
│   └── services/            Lógica de negocio
├── frontend/                Aplicación web React
│   ├── src/
│   │   ├── api/             Clientes HTTP al backend
│   │   ├── components/      Componentes reutilizables
│   │   ├── hooks/           Hooks personalizados
│   │   └── pages/           Páginas de la aplicación
│   └── vite.config.js       Dev server + proxy al backend
├── ml-models/               Módulo de inteligencia artificial
│   └── datosSinteticos.py   Generación de datasets sintéticos de diabetes
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
└── ARQUITECTURA PASO A PASO.md   Documentación detallada de la arquitectura
```

## Instalación y ejecución (app: frontend + backend)

### Requisitos previos

- Python 3.11+
- Node.js 18+
- npm

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
Documentación interactiva (Swagger) en `http://127.0.0.1:9999/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en `http://localhost:5500`.
Vite actúa como proxy, redirigiendo las peticiones API al backend automáticamente.

## API Endpoints principales

Todos los endpoints de negocio estan bajo el prefijo `/api`:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/api/auth/login` | Iniciar sesión |
| `GET`  | `/api/auth/me` | Usuario actual |
| `POST` | `/api/patients` | Crear paciente |
| `GET`  | `/api/patients` | Listar pacientes |
| `POST` | `/api/patients/bulk-import` | Importar pacientes desde Excel |
| `POST` | `/api/enrollments/{tipo}` | Crear empadronamiento |
| `GET`  | `/api/enrollments/{tipo}` | Listar empadronamientos |
| `POST` | `/api/medications` | Crear medicamento |
| `GET`  | `/api/medications` | Listar medicamentos |
| `POST` | `/api/monodrugs` | Crear monodroga |
| `GET`  | `/api/monodrugs` | Listar monodrogas |
| `POST` | `/api/agreements` | Crear acuerdo |
| `GET`  | `/api/agreements` | Listar acuerdos |
| `POST` | `/api/prescriptions` | Crear prescripción |
| `GET`  | `/api/prescriptions` | Listar prescripciones |
| `GET`  | `/api/ledger` | Bloques del ledger |
| `GET`  | `/api/ledger/verify` | Verificar integridad |

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

- Los datos del backend se almacenan **en memoria**; se pierden al reiniciar el servidor.
- El campo `blockchain_tx_id` en los modelos de paciente y empadronamiento está preparado para vincular cada registro con su transacción en blockchain (pendiente de integración).
- La carpeta `ml-models/` contiene los scripts de generación de datos sintéticos y será el módulo donde se implementen los modelos de IA del proyecto.
