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

La aplicacion esta desplegada y **operativa** en:

**https://d3qe3o25c33oqd.cloudfront.net**

> Estado verificado el 18/08/2026 con 25/25 checks end-to-end: alta on-chain con
> TxID real de Fabric, ciclo completo de auditoria, cadena de hashes en
> `valido: true`, los 3 peers en verde y la RDS sin rastro off-chain. El detalle
> del despliegue y de los bloqueantes que aparecieron esta en
> [docs/06-deploy-cambios-onchain.md](docs/06-deploy-cambios-onchain.md).

### Arquitectura en la nube

| Capa | Servicio AWS | Identificador | Descripcion |
|------|-------------|---------------|-------------|
| **Frontend** | S3 + CloudFront | `E3UXMQZNKANQDB` | SPA estatica servida con HTTPS |
| **Entrada API** | API Gateway HTTP API + VPC Link | `vl5nsf5jt5` / `q6olhm` | Enruta al backend por red privada |
| **Service discovery** | Cloud Map | `srv-ty4v27ve53xropsy` | Registros **SRV** (IP + puerto); ECS registra sus tasks solo |
| **Backend** | ECS Fargate | `medchain-backend-svc`, task def `:5` | Contenedor Docker serverless |
| **Datos maestros** | RDS PostgreSQL 16 | `medchain-db` | Usuarios, pacientes (PHI cifrada), medicamentos |
| **Blockchain** | EC2 `t3.large` | `i-0331b3fbeaadee294` | Orderer + 3 peers + 3 CouchDB + gateway |
| **Conectividad** | VPC peering | `pcx-040412e3bff5c43a4` | Une `medchain-vpc` (10.0/16) con la VPC de la EC2 (172.31/16) |
| **Secretos** | Secrets Manager | `medchain/*` | auth, base, clave de cifrado, PAT de GitHub |

El backend llega al gateway de Fabric por la **IP privada** `172.31.89.189:8081`
a traves del peering: ese puerto solo acepta trafico desde `10.0.0.0/16` y el
trafico nunca sale a internet.

> Inventario completo con todos los IDs en
> [docs/06 §9](docs/06-deploy-cambios-onchain.md).

### URLs de produccion

| Recurso | URL |
|---------|-----|
| App (usuario final) | `https://d3qe3o25c33oqd.cloudfront.net` |
| API Gateway (directo) | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com` |
| Health check | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/` |
| Swagger | `https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/docs` |

### Guias de despliegue

> **Empeza por aca si no conoces el sistema:**
> [docs/07-como-funciona-todo.md](docs/07-como-funciona-todo.md) explica de forma
> didactica como quedo todo — infraestructura, frontend, backend y blockchain —
> y sigue una prescripcion de punta a punta.

- **Despliegue on-chain en AWS (que se hizo y con que se tropezo):** [docs/06-deploy-cambios-onchain.md](docs/06-deploy-cambios-onchain.md)
- **Paso a paso por consola web:** [docs/05-deploy-aws-consola.md](docs/05-deploy-aws-consola.md)
- **Scripts automatizados (CLI):** ver carpeta `deploy/`
- **Blockchain en EC2:** [docs/04-aws-ec2-setup.md](docs/04-aws-ec2-setup.md)
- **Convencion de hashing verificable:** [docs/HASHING.md](docs/HASHING.md)

### Actualizar en produccion

> Lo normal es **pushear a `desarrollo`** y dejar que el pipeline haga el
> trabajo, o usar *Run workflow* si no hay cambios de codigo. Los comandos
> manuales de abajo quedan como via de escape: no verifican rollback ni corren
> los tests.

#### Frontend (manual)

```bash
cd frontend
npm run build
aws s3 sync dist/ s3://medchain-frontend-007072540405-007072540405-us-east-1-an/ --delete
aws cloudfront create-invalidation --distribution-id E3UXMQZNKANQDB --paths '/*'
```

#### Backend (manual)

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 007072540405.dkr.ecr.us-east-1.amazonaws.com
docker build -t medchain-backend .
docker tag medchain-backend:latest 007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
docker push 007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
aws ecs update-service --cluster medchain-cluster --service medchain-backend-svc --force-new-deployment --region us-east-1
```

### Apagar y volver a encender (ahorro de costos)

El orden importa, sobre todo al encender.

> ⚠️ **Nunca uses `network.sh down` para apagar.** Ese comando hace
> `docker compose down --volumes` y ademas borra `organizations/`: te destruye
> **el ledger y el material criptografico**. Es para rehacer la red de cero.
> Para apagar alcanza con detener la EC2.

**Bajar** — de arriba hacia abajo:

```bash
# 1. ECS a cero primero, para que no quede crasheando contra servicios caidos
aws ecs update-service --cluster medchain-cluster --service medchain-backend-svc \
  --desired-count 0 --region us-east-1

# 2. La EC2 (los contenedores de Fabric se detienen con ella)
aws ec2 stop-instances --instance-ids i-0331b3fbeaadee294 --region us-east-1

# 3. La base
aws rds stop-db-instance --db-instance-identifier medchain-db --region us-east-1
```

**Levantar** — de abajo hacia arriba, respetando las esperas:

```bash
# 1. RDS PRIMERO: el backend hace fail-fast y corre migraciones al arrancar
aws rds start-db-instance --db-instance-identifier medchain-db --region us-east-1
aws rds wait db-instance-available --db-instance-identifier medchain-db --region us-east-1

# 2. La EC2
aws ec2 start-instances --instance-ids i-0331b3fbeaadee294 --region us-east-1
aws ec2 wait instance-running --instance-ids i-0331b3fbeaadee294 --region us-east-1

# 3. Levantar Fabric a mano: el compose NO declara `restart:`, asi que los
#    contenedores quedan apagados al bootear
aws ssm send-command --instance-ids i-0331b3fbeaadee294 \
  --document-name AWS-RunShellScript --region us-east-1 --timeout-seconds 600 \
  --parameters 'commands=["sudo -u ubuntu -H bash -lc \"cd ~/PFI-Proyecto-Final/fabric && ./network.sh up\"","sleep 20","curl -sf http://localhost:8081/health"]'

# 4. ECS al final, cuando el gateway ya responde
aws ecs update-service --cluster medchain-cluster --service medchain-backend-svc \
  --desired-count 1 --region us-east-1
aws ecs wait services-stable --cluster medchain-cluster --services medchain-backend-svc --region us-east-1

# 5. Verificar
curl -s https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/
#    esperado: "database":"connected" y "fabric_gateway":"ok"
```

Tres cosas que no hace falta rehacer:

- **La IP privada de la EC2 no cambia** al detenerla (AWS la conserva mientras la
  instancia exista), asi que `FABRIC_GATEWAY_URL` sigue siendo valida. La
  **publica** si cambia, pero no la usa el sistema — solo vos para SSH.
- **El ledger sobrevive**: los volumenes (`orderer.medchain.com`, `peer0.*`) son
  *named volumes* de Docker y no se borran al detener contenedores.
- **`network.sh up` es idempotente**: ve que `organizations/` ya existe, saltea la
  generacion de criptografia y solo arranca los contenedores.

> AWS **reinicia sola** una instancia RDS detenida a los 7 dias. Si la vas a
> dejar apagada mas tiempo, tenelo presente.

### Limpieza de recursos

```bash
bash deploy/99-cleanup.sh
```

### CI/CD (GitHub Actions)

Hay dos workflows. **`ci.yml`** corre en cada push a `desarrollo` y en cada PR;
**`deploy.yml`** solo cuando cambian rutas que afectan a produccion.

#### Orden de ejecucion de `deploy.yml`

```
┌──────────────────┐   ┌──────────────────┐
│  security-scan   │   │     changes      │   ← arrancan juntos
│   (gitleaks)     │   │ (filtro de paths)│
└────────┬─────────┘   └────────┬─────────┘
         └──────────┬───────────┘
                    │  ambos deben pasar
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
┌─────────┐   ┌──────────┐   ┌────────────┐
│ backend │   │ frontend │   │ blockchain │   ← en PARALELO entre si
└─────────┘   └──────────┘   └────────────┘
```

**Los tres jobs de deploy corren en paralelo y no se esperan entre si.** Es
seguro porque el backend tolera que el gateway de Fabric no responda: arranca
igual y contesta `503` en las operaciones de prescripciones hasta que la red
vuelve. Lo que **no** tolera es que falte una variable de entorno o que la base
no este disponible (fail-fast, ver mas abajo).

`security-scan` es bloqueante: si gitleaks encuentra un secreto, no se despliega
nada.

#### Que despliega cada job

| Job | Se dispara con | Que hace |
|-----|----------------|----------|
| `deploy-backend` | `backend/**`, `sql/**`, `alembic/**`, `ml_models/artefactos/**`, `Dockerfile`, `requirements.txt` | Build + push a ECR, `update-service` en ECS, espera estabilidad y **verifica que ECS no haya revertido** |
| `deploy-frontend` | `frontend/**` | `npm run build`, sync a S3, invalidacion de CloudFront |
| `deploy-blockchain` | `chaincode/**`, `fabric-gateway-svc/**`, `fabric/**` | Por SSM en la EC2: `git reset --hard`, `deployCC`, rebuild del gateway y smoke test de `/health` |

#### Deteccion de rollback (importante)

El servicio ECS tiene `deploymentCircuitBreaker.rollback=true`: si las tasks
nuevas no arrancan, ECS **revierte a la revision anterior y el servicio queda
estable igual**. Un `aws ecs wait services-stable` a secas retorna 0 y el
pipeline quedaria **verde sobre un despliegue fallido** — exactamente lo que
paso el 17/08/2026.

Por eso `deploy-backend` guarda el ID del deployment que crea y verifica despues
que siga siendo el `PRIMARY` con `rolloutState=COMPLETED`. Si ECS revirtio,
falla el job y vuelca los eventos del servicio y los logs de la task muerta.

#### Redespliegue manual (`workflow_dispatch`)

Desde **Actions → Deploy to AWS → Run workflow** se puede desplegar sin
commitear, eligiendo por checkbox que componente. Sirve despues de rehacer la
red Fabric, rotar un secreto o reponer una task definition.

En ese modo los filtros de paths no aplican: manda lo que se elige.

#### Configuracion necesaria (una sola vez)

**GitHub → Settings → Secrets and variables → Actions:**

| Secret | Valor |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Access Key del usuario IAM `medchain-admin` |
| `AWS_SECRET_ACCESS_KEY` | Secret Key del usuario IAM `medchain-admin` |

El deploy de blockchain usa **AWS SSM Run Command** (no SSH): la EC2 solo
necesita el agente SSM y su rol IAM.

> El repositorio es **privado**, asi que la EC2 necesita credenciales para hacer
> `git pull`. Se resuelve con un credential helper
> (`/usr/local/bin/git-credential-medchain`) que lee el PAT desde el secreto
> `medchain/github-token` usando el instance role: el token no queda en disco ni
> viaja por los parametros de SSM. Para rotarlo alcanza con un
> `put-secret-value` sobre ese secreto, sin tocar la instancia.

## Usuarios de la aplicacion

`AuthService._seed_users()` siembra cuatro cuentas al primer arranque con base
disponible. **Son contraseñas por defecto**: cambialas desde la pantalla de
Usuarios (`super_admin`) antes de exponer la app.

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `superadmin` | `super123` | super_admin |
| `admin` | `admin123` | administrador |
| `prescriptor` | `presc123` | prescriptor |
| `auditor` | `audit123` | auditor |

El seed es idempotente (solo inserta si el usuario no existe), asi que rotarlas
es seguro: no se reponen en el proximo deploy. Minimo 8 caracteres.

## Notas

- Si `DATABASE_URL` esta configurada, los datos maestros persisten en PostgreSQL. Sin ella, se usa almacenamiento en memoria (los datos se pierden al reiniciar).
- Las **prescripciones y su auditoria viven exclusivamente en Hyperledger Fabric**: la RDS solo guarda usuarios/sesiones, monodrogas, medicamentos y pacientes (PHI cifrado con AES-256-GCM + indices ciegos).
- `FABRIC_GATEWAY_URL` y `GATEWAY_AUTH_TOKEN` son obligatorias en produccion: sin la red Fabric no se pueden crear ni auditar prescripciones (fail-fast).
- La carpeta `ml_models/` contiene el pipeline de entrenamiento del modelo de validacion de prescripciones (cancer de colon) y los artefactos asociados.
- La convencion de hashing verificable (payload canonico + cadena de eventos de auditoria) esta documentada en [docs/HASHING.md](docs/HASHING.md).
- La canonicalizacion **normaliza los flotantes enteros** (`174.0` → `174`) antes de hashear: CouchDB los devuelve asi, y sin esa normalizacion el asset releido nunca reproduce su propio `payload_hash`.
- La politica de endorsement es `AND` de las tres organizaciones. Es la garantia central del sistema y tiene un costo explicito: **si un peer se cae, no se puede escribir nada**. Visible en la pantalla de Salud y en `/health`.
- El chaincode incluye **indices CouchDB** en `META-INF/statedb/couchdb/indexes/`. Sin ellos las consultas con `sort` (listado, cola de auditoria, historial por paciente) fallan en runtime aunque el alta funcione.
