# MedChain AI

Sistema de auditoría de prescripciones oncológicas de alta complejidad con validación híbrida (reglas + ML) y registro inmutable en blockchain privada (Hyperledger Fabric).

Proyecto Final de Ingeniería Informática (UADE).

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| **Frontend** | React + Vite (puerto 5500) |
| **Backend** | Python 3.11 + FastAPI (puerto 9999) |
| **Modelo IA** | LightGBM (validación de concordancia de prescripciones de cáncer de colon) |
| **Blockchain** | Hyperledger Fabric 2.5 LTS (red propia, ver `fabric/`) |
| **Smart Contract** | Go |

## Estructura del proyecto

```
├── backend/                 API REST en Python
│   ├── main.py              Punto de entrada (FastAPI + Uvicorn)
│   ├── db.py                Conexion a PostgreSQL (pool, context manager, fallback en memoria)
│   ├── auth_middleware.py   Middleware de autenticacion y RBAC
│   ├── dependencies.py      Inyeccion de dependencias (singleton repos/services)
│   ├── models/              Modelos Pydantic (patient, prescription on-chain, audit, medication, etc.)
│   ├── repositories/        Repos de datos maestros (PostgreSQL) + FabricPrescriptionRepository
│   ├── routers/             Endpoints de la API con autenticacion y control de roles (4 roles)
│   ├── blockchain/          Cliente HTTP del puente fabric-gateway-svc
│   ├── security/            Cifrado PHI, Argon2id, JSON canonico + verificacion de hashes
│   └── services/            Logica de negocio (validacion ML, prescripciones, auditoria, usuarios)
├── sql/                     Queries SQL externalizadas (solo datos maestros y sesiones)
│   ├── schema.sql           DDL de todas las tablas
│   ├── patients.sql         Queries de pacientes
│   ├── medications.sql      Queries de medicamentos
│   ├── monodrugs.sql        Queries de monodrogas
│   ├── auth_tokens.sql      Queries de sesiones persistentes
│   └── users.sql            Queries de usuarios
├── frontend/                Aplicacion web React
│   ├── src/
│   │   ├── api/             Clientes HTTP al backend (patients, medications, monodrugs, prescriptions, audit)
│   │   ├── auth/            Contexto de autenticacion y proteccion de rutas con RBAC
│   │   ├── components/      Componentes reutilizables (Layout, Sidebar con menu por roles)
│   │   ├── hooks/           Hooks personalizados
│   │   └── pages/           Paginas de la aplicacion (incluye auditoria)
│   └── vite.config.js       Dev server + proxy al backend
├── ml_models/               Pipeline de entrenamiento y artefactos del modelo
│   ├── entrenar_modelo.py   Pipeline completo dataset + entrenamiento GBM
│   ├── reentrenar_desde_dataset.py  Reentrenamiento desde CSV/parquet local
│   ├── test_paridad_features.py     Test train/serve de features
│   └── artefactos/          modelo_gbm.joblib + metricas
├── backend/ml/              Nucleo compartido (regimenes, guias, codificacion, dosis, reglas)
├── chaincode/               Chaincode de prescripciones (fuente de verdad on-chain)
│   └── prescription-contract/   CreatePrescription, AuditPrescription, queries + tests Go
├── fabric-gateway-svc/      Puente HTTP -> Fabric Gateway SDK (una identidad por org)
├── fabric/                  Infraestructura de la red Hyperledger Fabric (3 orgs + CouchDB)
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
| `ML_MODEL_PATH` | Ruta al artefacto LightGBM (`modelo_gbm.joblib`). Si no se define, se usa `ml_models/artefactos/modelo_gbm.joblib` |

#### Persistencia dual

El backend soporta dos modos de persistencia:

- **PostgreSQL**: Si `DATABASE_URL` esta configurada, todos los repositorios usan la base de datos. Las tablas se crean automaticamente al iniciar (`sql/schema.sql`).
- **En memoria**: Si `DATABASE_URL` no esta definida, los datos se almacenan en listas Python y se pierden al reiniciar.

#### Roles y permisos (RBAC)

El sistema soporta cuatro roles con permisos diferenciados:

| Rol | Acceso |
|-----|--------|
| `super_admin` | ABM de usuarios y roles + acceso total a todos los modulos |
| `administrador` (administrativo) | Datos maestros: pacientes, medicamentos, monodrogas |
| `prescriptor` | Crea prescripciones (ejecuta el motor ML antes de asentarlas en Fabric); lectura de pacientes y catalogos |
| `auditor` | Cola de auditoria, acciones aprobar/rechazar/revision, trazabilidad |

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
| `POST` | `/api/prescriptions` | prescriptor, super_admin | Crear prescripcion: motor hibrido + asiento sincrono en Fabric |
| `GET`  | `/api/prescriptions` | prescriptor, auditor, super_admin | Listar desde Fabric (bookmark, filtro por estado) |
| `GET`  | `/api/prescriptions/{id}` | prescriptor, auditor, super_admin | Detalle del asset on-chain |
| `GET`  | `/api/prescriptions/{id}/history` | prescriptor, auditor, super_admin | Historial de transacciones Fabric (tx_id reales) |
| `GET`  | `/api/prescriptions/{id}/verify` | prescriptor, auditor, super_admin | Verifica la cadena de hashes (ver docs/HASHING.md) |
| `GET`  | `/api/prescriptions/regimenes` | prescriptor, auditor, super_admin | Catalogo de regimenes R00-R13 |
| `GET`  | `/api/prescriptions/dosis-referencia` | prescriptor, super_admin | Dosis de referencia por regimen |
| `POST` | `/api/prescriptions/recomendacion` | prescriptor, super_admin | Sugerir regimen segun guias (sin ML) |
| `GET`  | `/api/audit/queue` | auditor, super_admin | Cola de auditoria (PENDIENTE_AUDITORIA / EN_REVISION) |
| `GET`  | `/api/audit/{id}` | auditor, super_admin | Detalle para auditar (asset + historial) |
| `POST` | `/api/audit/{id}/accion` | auditor, super_admin | Accion on-chain: revision, aprobar o rechazar |
| `GET`  | `/api/users` | super_admin | Listar cuentas |
| `POST` | `/api/users` | super_admin | Crear cuenta con rol |
| `PUT`  | `/api/users/{id}` | super_admin | Editar nombre, rol y estado |
| `POST` | `/api/users/{id}/password` | super_admin | Resetear contrasena |
| `GET`  | `/api/health` | super_admin | Salud detallada (DB, ML, gateway, peers) |

## Blockchain

### Prescripciones 100% on-chain

La prescripcion **no se guarda en la RDS**: vive exclusivamente en el world
state de Fabric (chaincode `chaincode/prescription-contract/`, nombre logico
`prescriptions`). El asset porta el payload clinico completo (seudonimizado
via `patient_id`, sin PHI) mas el veredicto del motor reglas + ML, y el
chaincode administra el ciclo de auditoria:

```
PENDIENTE_AUDITORIA ──> EN_REVISION ──> APROBADA | RECHAZADA
        └──────────────────────────────────┘  (dictamen directo)
```

- `CreatePrescription` — solo **PrescriptorMSP**. Hashea el payload canonico
  (`payload_hash`) y crea el asset en estado `PENDIENTE_AUDITORIA`.
- `AuditPrescription` — solo **MedChainMSP**. Valida la transicion de estado
  y encadena un nuevo hash por cada accion (`event_hash`, ver
  [docs/HASHING.md](docs/HASHING.md)).
- `GetPrescription`, `ListPrescriptions`, `QueryPrescriptionsByEstado`,
  `QueryPrescriptionsByPatient`, `GetPrescriptionHistory` — lectura para las
  tres organizaciones (rich queries con paginacion por bookmark, CouchDB).

El backend llega a la red a traves de **fabric-gateway-svc** (Go +
Fabric Gateway SDK), que mantiene una identidad por organizacion y firma cada
transaccion segun el actor: prescriptor → PrescriptorMSP, auditor →
MedChainMSP, lecturas → PrepagaMSP. La escritura es **sincrona** dentro del
request: si la red no responde, el alta falla con 503 (no hay copia off-chain).

### Red Hyperledger Fabric (`fabric/`)

La carpeta `fabric/` contiene una red **Hyperledger Fabric 2.5 LTS** reproducible desde cero:

- **3 organizaciones** que monitorean que no haya adulteraciones, cada una con 1 peer + CouchDB:
  - `PrescriptorMSP` (`prescriptor.medchain.com`) — el centro prescriptor.
  - `MedChainMSP` (`auditoria.medchain.com`) — la empresa auditora MedChain.
  - `PrepagaMSP` (`prepaga.medchain.com`) — el financiador / prepaga.
- **Politica de endorsement explicita** `AND('PrescriptorMSP.peer','MedChainMSP.peer','PrepagaMSP.peer')`:
  ninguna transaccion entra al ledger sin la firma de las tres organizaciones.
- **1 orderer** (consenso Raft / etcdraft), usando la *Channel Participation API* (sin system channel).
- **Material criptográfico** generado con `cryptogen` (`User1@<org>` es la identidad del gateway).
- **Chaincode** `prescriptions` (`chaincode/prescription-contract/`) escrito en **Go**.
- **Canal** de aplicación: `mychannel`.
- Antes de levantar: `cp fabric/network/.env.example fabric/network/.env` y ajustar valores.

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

> Para entender **como funciona todo** (infraestructura, frontend, backend y
> blockchain) antes de meterse con el despliegue:
> [docs/07-como-funciona-todo.md](docs/07-como-funciona-todo.md).

- **Cambios on-chain (que falta para deployarlos):** [docs/06-deploy-cambios-onchain.md](docs/06-deploy-cambios-onchain.md)
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
- Si cambia `chaincode/`, `fabric-gateway-svc/` o `fabric/` -> via AWS SSM en la EC2: git pull, redeploy del chaincode (secuencia automatica) y rebuild del gateway, con smoke test de `/health`.
- Los tres jobs corren en paralelo si hay cambios en multiples componentes.

**Configuracion necesaria (una sola vez):**

Ir a **GitHub > Settings > Secrets and variables > Actions** y crear estos secrets:

| Secret | Valor |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Access Key del usuario IAM `medchain-admin` |
| `AWS_SECRET_ACCESS_KEY` | Secret Key del usuario IAM `medchain-admin` |

El deploy de blockchain usa **AWS SSM Run Command** (no SSH): la EC2 solo necesita el agente SSM y el rol IAM correspondiente.

El workflow se encuentra en `.github/workflows/deploy.yml`.

## Notas

- Si `DATABASE_URL` esta configurada, los datos maestros persisten en PostgreSQL. Sin ella, se usa almacenamiento en memoria (los datos se pierden al reiniciar).
- Las **prescripciones y su auditoria viven exclusivamente en Hyperledger Fabric**: la RDS solo guarda usuarios/sesiones, monodrogas, medicamentos y pacientes (PHI cifrado con AES-256-GCM + indices ciegos).
- `FABRIC_GATEWAY_URL` y `GATEWAY_AUTH_TOKEN` son obligatorias en produccion: sin la red Fabric no se pueden crear ni auditar prescripciones (fail-fast).
- La carpeta `ml_models/` contiene el pipeline de entrenamiento del modelo de validacion de prescripciones (cancer de colon) y los artefactos asociados.
- La convencion de hashing verificable (payload canonico + cadena de eventos de auditoria) esta documentada en [docs/HASHING.md](docs/HASHING.md).
