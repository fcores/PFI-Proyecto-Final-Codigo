# 06 — Deploy en AWS de los cambios on-chain

Documento de handoff del refactor **"prescripciones 100% on-chain + red de 3
organizaciones + 4 roles"** (agosto 2026). Cubre qué cambió, qué quedó
verificado y **qué falta hacer en AWS** para dejarlo funcionando.

> **Revisado el 18/08/2026** contra el código (`desarrollo`, `578a309`) y contra
> la cuenta AWS `007072540405`. El código está completo; **la infraestructura no**:
> el deploy del backend nuevo se intentó el 17/08, falló y ECS lo revirtió
> (sección 3.1). Las secciones 3, 4.2, 4.5, 4.6, 4.7, 5 y 8 reflejan el estado real.

> Alcance: solo estos cambios. La infraestructura base (VPC, ECS, RDS, S3,
> CloudFront, API Gateway, EC2) ya existe y se documenta en
> [05-deploy-aws-consola.md](05-deploy-aws-consola.md) y
> [04-aws-ec2-setup.md](04-aws-ec2-setup.md).

---

## 1. Contexto: qué cambió

### 1.1 Decisiones de arquitectura

| Antes | Ahora |
|---|---|
| Prescripción completa en la RDS (~40 columnas) | **Sin rastro en la RDS**: vive solo en el world state de Fabric |
| "Blockchain" = ledger interno SHA-256 en Postgres | **Retirado**. La fuente de verdad es Hyperledger Fabric |
| Red de 2 orgs genéricas (Org1/Org2), LevelDB | **3 orgs con semántica**: PrescriptorMSP, MedChainMSP, PrepagaMSP + CouchDB por peer |
| Endorsement implícito `MAJORITY` | **Explícito `AND` de las 3 orgs**: nadie escribe sin la firma de todos |
| `fabric-gateway-svc` era un stub (tx_id falsos) | **Gateway real** con Fabric Gateway SDK, una identidad X509 por organización |
| Escritura a Fabric por outbox asíncrono (apagado) | **Escritura síncrona** en el request; si Fabric no responde → HTTP 503 |
| Solo REVISION/RECHAZADO iban a auditoría | **Todas** las prescripciones nacen `PENDIENTE_AUDITORIA` |
| Dictamen + correcciones campo a campo | Acciones del auditor: **aprobar / rechazar / revisión** (sin correcciones) |
| 3 roles, sin ABM de usuarios | **4 roles** (nuevo `super_admin`) + CRUD de usuarios por API |
| Passwords SHA-256, sesiones en RAM | **Argon2id** (migración transparente) + sesiones en tabla `auth_tokens` |

### 1.2 Ciclo de vida on-chain

```
PENDIENTE_AUDITORIA ──revision──> EN_REVISION ──aprobar/rechazar──> APROBADA | RECHAZADA
        └──────────── aprobar/rechazar (dictamen directo) ─────────────┘
```

El chaincode valida las transiciones y encadena un hash por cada acción
(`payload_hash` → `event_hash₁` → `event_hash₂` …). La convención completa y
verificable está en [HASHING.md](HASHING.md); el endpoint
`GET /api/prescriptions/{id}/verify` la comprueba.

### 1.3 Componentes tocados

| Componente | Cambio |
|---|---|
| `chaincode/prescription-contract/` | Reescrito: asset completo, máquina de estados, control por MSP, hashing encadenado, rich queries paginadas + tests Go. Incluye `META-INF/statedb/couchdb/indexes/` (sin esos índices las queries con `sort` fallan en runtime) |
| `fabric-gateway-svc/` | De stub a puente real (SDK, 3 identidades, auth por token, mapeo de errores) + Dockerfile |
| `fabric/` | 3 orgs + CouchDB, política de endorsement explícita, `.env.example`, scripts actualizados |
| `backend/` | Prescripciones/auditoría contra Fabric; se eliminan ledger, outbox y repos off-chain; módulo de usuarios; Argon2id; sesiones persistentes |
| `sql/` + `alembic/` | Migración **006** (rol `super_admin` + `auth_tokens`) y **007** (DROP de las 6 tablas off-chain) |
| `frontend/` | 4 roles, gestión de usuarios, salud del sistema, cola de auditoría nueva, paginación por bookmark, trazabilidad desde Fabric |
| `.github/workflows/` | CI con jobs Go; deploy de blockchain sin `continue-on-error`, con rebuild del gateway y smoke test; `deploy-backend` detecta el rollback de ECS |
| `deploy/04-ecs-cluster.sh` | Task definition con `FABRIC_GATEWAY_URL` + `GATEWAY_AUTH_TOKEN` + `ENCRYPTION_SECRET_ARN`; guards de variables faltantes |
| `deploy/03-secrets-iam.sh` | Policy del execution role con `SECRET_ARN` **y** `DB_SECRET_ARN`; task role con acceso a la clave de cifrado |
| `deploy/05-api-gateway.sh` | Resuelve el Cloud Map service filtrando por namespace y valida que coincida con el que usa ECS |

**Eliminados**: `blockchain/` (contrato legacy con PHI en claro),
`chaincode/asset-transfer-basic/`, `backend/services/ledger_service.py`,
`backend/blockchain/outbox_worker.py`, `backend/repositories/{prescription,audit,ledger}_repo.py`,
`sql/{prescriptions,audit,ledger}.sql`, `frontend/src/api/ledger.js`.

---

## 2. Estado: qué está verificado y qué no

### Verificado localmente

- `pytest`: **52 tests OK** (fake del chaincode con la misma semántica, vectores de hash compartidos Python↔Go, flujo completo de auditoría, ABM de usuarios, migración de passwords). Hay 55 definidos: los 3 de `test_schema_drift.py` se saltean sin `TEST_DATABASE_URL` y solo corren en CI.
- `ruff` y `black` limpios sobre `backend/` y `tests/`.
- La app FastAPI levanta y expone sus **26 paths** (= 30 operaciones HTTP bajo `/api` más el endpoint raíz `/`; si contás métodos y no paths, el número que vas a ver es 31).
- `npm run build` del frontend compila sin errores.

### NO verificado todavía (faltaban Go, Docker y Postgres en la máquina de desarrollo)

| Qué | Dónde se verifica |
|---|---|
| Compilación del chaincode y sus tests Go | Job `chaincode-tests` del CI (al pushear) |
| Compilación del gateway | Job `gateway-build` del CI |
| Paridad `sql/schema.sql` ↔ Alembic | Job `backend-tests` del CI (usa Postgres real) |
| Levantar la red de 3 orgs y desplegar el chaincode | **Manual en la EC2** (sección 4) |
| Flujo end-to-end (alta → cola → dictamen → trazabilidad) | **Manual, post-deploy** (sección 7) |

---

## 3. Qué falta en AWS — resumen

> **Ejecutado el 18/08/2026** contra la cuenta `007072540405`. El sistema quedó
> operativo y verificado end-to-end (25/25 checks, ver sección 7). Esta tabla
> queda como registro de lo que hubo que hacer.

| # | Tarea | Dónde | Estado |
|---|---|---|---|
| 1 | Agregar `GATEWAY_AUTH_TOKEN` al secreto de Secrets Manager | Secrets Manager | **Hecho** |
| 2 | Conectividad ECS ↔ EC2:8081 por **VPC peering** | VPC / SG | **Hecho** (`pcx-040412e3bff5c43a4`) |
| 3 | Nueva revisión de la task definition | ECS | **Hecho** (`medchain-backend:5`) |
| 4 | Red Fabric de 3 orgs + gateway | EC2 | **Hecho** |
| 5 | Backup de la RDS antes de la 007 | RDS | **Hecho** (`medchain-pre-007-20260818`) |
| 6 | ~~`ENCRYPTION_SECRET_ARN` en la task definition~~ | ECS | Ya estaba — ver 4.6 |
| 7 | Cambiar las contraseñas de las **4** cuentas sembradas | App | **PENDIENTE — lo tenés que hacer vos** |
| 8 | Repuntar API Gateway al Cloud Map correcto | API GW | **Hecho** (`srv-ty4v27ve53xropsy`, registros SRV) |

> ⚠️ **Lo único que queda pendiente es la tarea 7.** Las cuatro cuentas siguen
> con las contraseñas sembradas (`superadmin/super123`, `admin/admin123`,
> `prescriptor/presc123`, `auditor/audit123`). Cambialas desde la pantalla de
> Usuarios antes de exponer la app a cualquiera.

### 3.1 El deploy del 17/08 falló y ECS lo revirtió

Al pushear el refactor, el pipeline quedó **en verde** pero el backend nuevo
**nunca entró en servicio**:

```
17:42  push de la imagen nueva a ECR
17:42-17:45  ECS arranca 4 tasks; las 4 crashean
17:46  "deployment failed: tasks failed to start"
17:46  "rolling back to deployment ecs-svc/5878899130596736915"
17:48  "deployment completed"      ← vuelve a la imagen VIEJA
```

Causa, en el log de la task fallida:

```
RuntimeError: FABRIC_GATEWAY_URL es obligatoria en ENVIRONMENT=production:
las prescripciones viven exclusivamente en la red Fabric.
```

O sea: **el fail-fast funcionó como estaba diseñado** y frenó el deploy porque las
tareas 1-3 de esta tabla no estaban hechas. Consecuencias a tener presentes:

- **Hoy corre código pre-refactor.** El discriminante rápido: el endpoint raíz
  responde sin el campo `fabric_gateway`.
- **El frontend nuevo sí se desplegó** (CloudFront sirve el bundle con
  `super_admin`, `bookmark`, `/auditoria/cola`). La app está inconsistente: UI
  nueva contra backend viejo.
- El pipeline quedó verde porque el servicio tiene
  `deploymentCircuitBreaker.rollback=true` y **alcanza steady state después de
  revertir**, así que `aws ecs wait services-stable` retorna éxito. Ya está
  corregido en `deploy.yml` con un paso que compara el ID del deployment
  `PRIMARY` antes y después (ver sección 6).

### 3.2 Bloqueantes que aparecieron al desatascar el deploy

Ninguno de estos se había ejercitado nunca: el `continue-on-error` del job de
blockchain y el rollback silencioso de ECS los mantenían ocultos. Todos están
corregidos en el repo; se listan porque explican por qué "el código estaba
completo" y aun así nada funcionaba.

| # | Síntoma | Causa | Corrección |
|---|---|---|---|
| 1a | Contenedor en crash loop, siempre en `Running upgrade 004 -> 005` | La migración 005 castea 5 columnas a JSONB, pero tienen `DEFAULT '[]'::text`. Postgres aborta con `default for column ... cannot be cast automatically to type jsonb` | 005 ahora hace `DROP DEFAULT` → `ALTER TYPE` → `SET DEFAULT '[]'::jsonb` |
| 1b | Ídem, después de corregir 1a | 005 crea `chk_users_role` con solo 3 roles, pero la base ya tiene `superadmin` con rol `super_admin` → `CheckViolation`. 005 es anterior al rol nuevo, que agrega la 006 | 005 omite la constraint si hay filas fuera del set (mismo criterio defensivo que sus bloques de FK); la 006 la recrea con los 4 roles |
| 2 | `go build` del gateway falla en la EC2 y en CI | `fabric-gateway v1.11.0` exige Go ≥ 1.25; el Dockerfile usaba 1.24 y `ci.yml` 1.23 | Go 1.25 en Dockerfile, `go.mod` y `ci.yml` |
| 3 | `peer lifecycle chaincode install` devuelve `invalid UTF-8` | El repo no versionaba `chaincode/.../go.sum`, así que `go mod vendor` fallaba y se empaquetaba un chaincode incompleto | `go.sum` versionado |
| 4 | `deployCC` aborta con `failed to determine module root: exec: "go": not found` | Go estaba instalado en la EC2 pero fuera del PATH de root, que es con quien corre SSM | Symlinks en `/usr/local/bin` + `/etc/profile.d/go.sh` en la EC2 |
| 5 | Gateway arriba pero las 3 orgs en error: `error leyendo clave privada: permission denied` | El contenedor corre como uid 10001 (no-root) y cryptogen genera las claves 600 del usuario del host | `network.sh` cede las identidades `User1` al uid 10001 antes de levantar |
| 6 | `git pull` en la EC2: `could not read Username for github.com` | El repo es **privado** y la instancia no tenía credenciales. También habría roto el job `deploy-blockchain` | PAT en Secrets Manager (`medchain/github-token`) + credential helper que lo resuelve con el instance role; el token no queda en disco |
| 7 | API Gateway pasa de 503 a **500** tras repuntar el Cloud Map | ECS registraba la instancia sin `AWS_INSTANCE_PORT` (el service usa registros A). API Gateway necesita el puerto para rutear | Cloud Map nuevo con registros **SRV** (`medchain-backend-srv`) y `serviceRegistries` con `containerName` + `containerPort` |
| 8 | `TestSinTimeNowEnElContrato` falla siempre | Hacía `strings.Contains(src, "time.Now(")` y matcheaba el **comentario** de `contract.go` que documenta la prohibición | Ahora inspecciona el AST buscando la llamada real |

| 9 | El job `deploy-blockchain` muere en el primer comando: `fatal: $HOME not set` | `AWS-RunShellScript` corre como root sin `HOME`, y `git config --global` lo necesita para ubicar `~/.gitconfig` | El job exporta `HOME`, agrega Go al `PATH` y corre git + `deployCC` como `ubuntu` (`-H`), que además es el dueño del repo |
| 10 | Backend arriba y `/` en `ok`, pero `GET /api/patients` responde 500: `the JSON object must be str, bytes or bytearray, not list` | La 005 pasa `patients.medications` de TEXT a JSONB. Como **nunca se había aplicado**, el cambio de tipo recién surtió efecto ahora: psycopg2 devuelve una lista ya deserializada y el repo le seguía aplicando `json.loads` | `patient_repo._load_medications()` acepta lista, dict o str, así que funciona contra una base migrada y contra una que todavía no lo está |
| 11 | Toda alta responde 409: `no combination of peers can be derived which satisfy the endorsement policy` | `configtx.yaml` no declaraba **`AnchorPeers`** en ninguna org. Sin anchor peers el gossip no cruza organizaciones: el Gateway SDK solo descubre los peers de su propia org y nunca puede reunir las tres firmas que exige la política AND | Se declaran los 3 anchor peers en `configtx.yaml`. Quedan en el bloque de génesis, así que **hay que rehacer el canal** |

| 12 | `GET /api/prescriptions/{id}/verify` devuelve `valido: false` con `payload_hash no coincide` para **toda** prescripción real | El chaincode no re-serializa el payload, pero el world state **sí pasa por CouchDB**, que normaliza los números: se hashea `"talla_cm":174.0` y al releer vuelve `"talla_cm":174`. La cadena de `event_hash` verificaba bien; fallaba solo la reconstrucción del payload | `canonical_json()` normaliza los floats integrales a entero antes de serializar, que es la forma que sobrevive el round-trip. Los vectores compartidos con Go usan enteros, así que no cambian |

| 13 | El job `deploy-blockchain` marca rojo aunque el despliegue termine bien | `aws ssm wait command-executed` agota sus reintentos a los ~100 s; `deployCC` instala en 3 peers y construye 3 contenedores, así que tarda varios minutos. El paso siguiente leía un estado todavía `InProgress` | Poll propio de hasta 15 min que corta ante cualquier estado terminal |
| 14 | El chequeo anti-rollback (agregado en esta misma tanda) fallaba deploys sanos | Leía `rolloutState` una sola vez apenas volvía `services-stable`, pero ECS marca `COMPLETED` unos segundos después | Poll acotado que corta apenas deja de ser `IN_PROGRESS`, o antes si cambió el `PRIMARY` (ahí sí hubo rollback) |

> **Los bloqueantes 11 y 12 son los más instructivos del lote**, y por el mismo
> motivo: el pipeline nunca ejercitó una **escritura**. La red levantaba, el
> canal se creaba, el chaincode se commiteaba y las lecturas andaban; el smoke
> test (`curl /health`) y el `ListPrescriptions` de `deployCC` pasaban los dos.
> El 11 rompía toda alta y el 12 invalidaba la garantía de no adulteración —que
> es la tesis del trabajo— y ninguno era visible sin dar de alta una
> prescripción y verificarla.
>
> **Mejora pendiente recomendada**: agregar al pipeline un alta contra un asset
> de descarte seguida de su `/verify`. Es el único smoke test que hubiera
> atrapado 11 y 12, y cuesta dos llamadas HTTP.

> Los tipos de registro de un service de Cloud Map **no se pueden cambiar**
> (`A` → `SRV` da `InvalidInput`): hay que crear un service nuevo y repuntar
> `serviceRegistries` del servicio ECS y la integración del API Gateway.

**Cómo diagnosticar migraciones sin gastar un ciclo de deploy.** Un fallo de
Alembic cuesta build + push + crash loop + rollback (~10 min) y el traceback se
pierde si el contenedor muere antes de que el driver `awslogs` haga flush. Como
la RDS es `PubliclyAccessible` y su SG ya permite las IPs de desarrollo, sale
mucho más barato extraer el SQL de cada migración y ejecutarlo contra la base
real dentro de una transacción con `ROLLBACK`. Así se encontraron 1a y 1b.

---

## 4. Detalle de las tareas

### 4.1 Secrets Manager — agregar `GATEWAY_AUTH_TOKEN`

El backend y el gateway comparten un token (header `X-Gateway-Token`). Hay que
agregarlo al secreto existente `medchain/auth-credentials` **conservando** las
claves actuales (`put-secret-value` reemplaza el JSON completo):

```bash
TOKEN=$(openssl rand -hex 32)
echo "Guardá este token, va también en la EC2: $TOKEN"

aws secretsmanager put-secret-value \
  --secret-id medchain/auth-credentials \
  --region us-east-1 \
  --secret-string "{\"AUTH_USERNAME\":\"admin\",\"AUTH_PASSWORD\":\"<la-actual>\",\"AUTH_DISPLAY_NAME\":\"Administrador\",\"GATEWAY_AUTH_TOKEN\":\"$TOKEN\"}"
```

> El execution role `medchain-ecs-execution-role` ya tiene permiso
> `secretsmanager:GetSecretValue` sobre este ARN, así que no hay cambios de IAM.
> **Verificar** que la policy también cubra el secreto de la base
> (`DB_SECRET_ARN`), que hoy está en un ARN distinto.

### 4.2 Conectividad ECS ↔ EC2 — VPC peering

**El problema**: las tasks ECS corren en `medchain-vpc`
(`vpc-0c98e7d7f299bf5e8`, `10.0.0.0/16`) con `assignPublicIp=ENABLED`, mientras
que la EC2 de Fabric (`i-0331b3fbeaadee294`, `t3.large`, tag `pfi-fabric`) vive
en la **VPC default** `vpc-09fcdbfb17d5cae13` (`172.31.0.0/16`) y **no la crea
ningún script del repo**. Además, el gateway habla **HTTP plano** en el 8081.

> **Ojo con la IP.** Versiones anteriores de este documento citaban
> `34.199.204.55`: esa dirección **no existe en la cuenta**. La IP pública real
> es dinámica (al 18/08 era `3.86.223.89`) y **no hay Elastic IP asociada** a la
> instancia, así que se pierde en cada stop/start. No la hardcodees en ningún lado.

**Decisión tomada: VPC peering.** Da tráfico privado sin recrear la instancia ni
perder lo ya instalado en ella (Docker, imágenes de Fabric).

1. **Peering** entre las dos VPCs (los CIDR no se solapan, así que es viable):

   ```bash
   PCX=$(aws ec2 create-vpc-peering-connection \
     --vpc-id vpc-0c98e7d7f299bf5e8 --peer-vpc-id vpc-09fcdbfb17d5cae13 \
     --region us-east-1 --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)
   aws ec2 accept-vpc-peering-connection --vpc-peering-connection-id "$PCX" --region us-east-1
   ```

2. **Rutas en los dos sentidos.** En la route table de las subredes de ECS
   (`subnet-0752770229746744b`, `subnet-0d27ce970f3922eda`) agregar
   `172.31.0.0/16 → $PCX`; en la de la EC2 (`subnet-060ce9a4001f1d824`),
   `10.0.0.0/16 → $PCX`.

3. **Security group de la EC2.** Entre VPCs peereadas **no sirve
   `--source-group`**: hay que autorizar por CIDR.

   ```bash
   aws ec2 authorize-security-group-ingress \
     --group-id sg-0c6d00bf321b64291 \
     --protocol tcp --port 8081 \
     --cidr 10.0.0.0/16 \
     --region us-east-1
   ```

4. **Aprovechar y cerrar el 1433.** Hoy `sg-0c6d00bf321b64291` expone los puertos
   22 y **1433 a `0.0.0.0/0`**. El 1433 no lo usa nada de este stack.

Resultado: `FABRIC_GATEWAY_URL=http://172.31.89.189:8081` (IP privada de la EC2),
tráfico que nunca sale a internet.

**Alternativas descartadas**: mover la EC2 a `medchain-vpc` (implica reinstalar
todo el stack de Fabric, no solo rehacer la red); Elastic IP pública + token
(expone el 8081 a internet con el token sin TLS, y además requiere asignar
primero una EIP que hoy no existe).

### 4.3 ECS — nueva revisión de la task definition

**Ojo**: el workflow de deploy hace `update-service --force-new-deployment`,
que **reutiliza la task definition vigente**. Las variables nuevas no se aplican
solas: hay que registrar una revisión nueva **una vez**.

1. Completar `deploy/.env.deploy` con la URL resuelta en 4.2:

   ```bash
   echo "FABRIC_GATEWAY_URL=http://<ip-privada-o-elastic-ip>:8081" >> deploy/.env.deploy
   ```

2. Registrar la revisión y apuntar el servicio (opción rápida con la task def
   actual como base):

   ```bash
   aws ecs describe-task-definition --task-definition medchain-backend \
     --region us-east-1 --query 'taskDefinition' > /tmp/td.json
   # editar /tmp/td.json: agregar en "environment"
   #   {"name":"FABRIC_GATEWAY_URL","value":"http://<ip>:8081"}
   # y en "secrets"
   #   {"name":"GATEWAY_AUTH_TOKEN","valueFrom":"<SECRET_ARN>:GATEWAY_AUTH_TOKEN::"}
   # (y, si se hace el punto 4.6, ENCRYPTION_SECRET_ARN)
   # quitar campos de solo lectura: taskDefinitionArn, revision, status,
   #   requiresAttributes, compatibilities, registeredAt, registeredBy

   aws ecs register-task-definition --cli-input-json file:///tmp/td.json --region us-east-1

   aws ecs update-service --cluster medchain-cluster --service medchain-backend-svc \
     --task-definition medchain-backend --force-new-deployment --region us-east-1
   ```

   La versión completa y correcta del bloque ya está en
   `deploy/04-ecs-cluster.sh` (líneas de `environment` / `secrets`), que
   además ahora **falla si `FABRIC_GATEWAY_URL`, `DB_SECRET_ARN` o
   `ENCRYPTION_SECRET_ARN` no están definidas**.

3. El health check del contenedor se ajustó a `timeout 10s` / `startPeriod 90s`
   porque `/` ahora consulta el gateway (con timeout propio de 2s). Si se
   registra la task def a mano, aplicar esos valores (la revisión 4 que está
   vigente todavía tiene `timeout 5` / `startPeriod 15`).

> **Fail-fast**: con `ENVIRONMENT=production`, el backend **no arranca** sin
> `DATABASE_URL`, `FABRIC_GATEWAY_URL` y `GATEWAY_AUTH_TOKEN`
> (`backend/config.py:57-75`). Si falta alguna, la task crashea al arrancar.
>
> **Lo que NO pasa**: que el pipeline se ponga en rojo solo. El servicio tiene
> `deploymentCircuitBreaker.rollback=true`, así que ECS revierte a la revisión
> anterior y **alcanza steady state igual** → `aws ecs wait services-stable`
> retorna éxito sobre un deploy fallado. Es exactamente lo que pasó el 17/08
> (sección 3.1). Por eso `deploy.yml` ahora agrega un paso que compara el ID del
> deployment `PRIMARY` antes y después, y falla si ECS lo revirtió.

### 4.4 EC2 — rehacer la red Fabric y levantar el gateway

El material criptográfico cambia por completo (3 organizaciones nuevas con
dominios nuevos), así que **no hay upgrade incremental**: se baja la red y se
levanta de cero. Los datos de demo previos en el ledger se pierden.

La IP pública es dinámica: obtenela en el momento en vez de copiarla de acá.

```bash
IP=$(aws ec2 describe-instances --instance-ids i-0331b3fbeaadee294 --region us-east-1 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

ssh -i mi-key.pem ubuntu@"$IP"
cd ~/PFI-Proyecto-Final
git fetch origin main && git checkout main && git pull

cd fabric
cp network/.env.example network/.env
# Editar network/.env:
#   GATEWAY_AUTH_TOKEN=<el mismo token de Secrets Manager (4.1)>
#   COUCHDB_USER / COUCHDB_PASSWORD

./network.sh down            # limpia la red vieja de 2 orgs
./network.sh up              # genera cripto de las 3 orgs + peers + CouchDB + gateway
./network.sh createChannel   # une orderer y los 3 peers a mychannel
./network.sh deployCC        # instala/aprueba/commitea con la política AND

curl -s --cacert fabric/network/gateway-tls/ca.crt https://localhost:8443/health | jq   # las 3 orgs deben responder "ok"
```

Sin acceso SSH a mano, el estado se puede inspeccionar por SSM (el agente está
`Online` en la instancia):

```bash
aws ssm send-command --instance-ids i-0331b3fbeaadee294 \
  --document-name AWS-RunShellScript --region us-east-1 \
  --parameters 'commands=["docker ps","curl -s --cacert /home/ubuntu/PFI-Proyecto-Final/fabric/network/gateway-tls/ca.crt https://localhost:8443/health"]'
```

**Índices de CouchDB**: el chaincode incluye
`chaincode/prescription-contract/META-INF/statedb/couchdb/indexes/` con un índice
por cada rich query. Se empaquetan e instalan junto con el chaincode en el
`deployCC`, así que **no hay paso manual** — pero si alguna vez se despliega sin
ellos, las queries con `sort` (listado, cola de auditoría, historial por paciente)
fallan en runtime con `No index exists for this sort`, aunque el alta funcione.
El test `TestRichQueriesTienenIndiceCouchDB` del CI impide que se desincronicen.

**Recursos**: la t3.large (8 GB) ahora corre orderer + 3 peers + 3 CouchDB +
3 contenedores de chaincode + gateway + cli ≈ 4–5 GB. Entra justo. Si aparecen
OOM o los builds de Go se vuelven lentos por agotamiento de CPU credits,
escalar a **t3.xlarge**.

De ahí en adelante, el workflow `deploy-blockchain` (SSM) hace `git pull` →
`deployCC` (con secuencia autodetectada) → rebuild del gateway → smoke test de
`/health`, y ya **no** es `continue-on-error`.

### 4.5 RDS — migraciones 006 y 007

Las migraciones corren **automáticamente** al arrancar el contenedor
(`python -m backend.db_bootstrap` en el `Dockerfile`), así que se aplican solas
en el deploy del backend.

- **006**: agrega el rol `super_admin` al CHECK y crea `auth_tokens`.
- **007**: **DROPea** `prescriptions`, `audit_cases`, `dictamenes`,
  `corrections`, `prescription_outbox`, `ledger_blocks`, la secuencia
  `prescription_id_seq` y la columna `patients.blockchain_tx_id`.

> **Backup previo obligatorio.** 007 no tiene vuelta atrás por Alembic:
> `downgrade()` lanza `NotImplementedError` a propósito. El snapshot es la
> **única** vía de rollback si el deploy sale mal.
>
> ```bash
> aws rds create-db-snapshot --db-instance-identifier medchain-db \
>   --db-snapshot-identifier medchain-pre-007-$(date +%Y%m%d) --region us-east-1
> aws rds wait db-snapshot-completed \
>   --db-snapshot-identifier medchain-pre-007-$(date +%Y%m%d) --region us-east-1
> ```
>
> Si hiciera falta conservar las prescripciones de demo, hay que escribir un
> script de backfill que las recree vía el gateway **antes** de aplicar 007
> (no está implementado).

Al primer arranque con base disponible, `AuthService._seed_users()` siembra
**cuatro** cuentas con contraseñas triviales (`backend/services/auth_service.py:69-74`):
`superadmin/super123`, `admin/admin123`, `prescriptor/presc123`, `auditor/audit123`.
El seed es idempotente (solo inserta si el usuario no existe), así que rotarlas
después del deploy es seguro.

### 4.6 Deuda previa: estado real

- **`ENCRYPTION_SECRET_ARN`: ya estaba resuelto en AWS.** La revisión
  `medchain-backend:4` lo trae como env var apuntando a
  `medchain/encryption-key-rHsa5p`, y el task role tiene `AllowEncryptionKeyRead`.
  El riesgo era el inverso: **`04-ecs-cluster.sh` no lo incluía**, así que
  registrar una revisión con ese script lo borraba. Ya está agregado al script.
  Va en `environment` y no en `secrets` a propósito: la app recibe el ARN y lee
  el secreto sola en runtime (`backend/security/key_manager.py`), usando el
  **task** role, no el execution role.
  > Detalle a saber: si falta, el error es **lazy** — la app levanta "sana" y
  > revienta recién en la primera operación con PHI de pacientes.
  > `validate_production_requirements()` no lo valida al arrancar.
- **Permiso `GetSecretValue` sobre `DB_SECRET_ARN`**: en AWS funciona gracias a
  una policy inline extra (`AllowDatabaseSecret`) agregada a mano al execution
  role. `03-secrets-iam.sh` solo creaba la policy con `SECRET_ARN`, así que
  re-ejecutarlo no la reponía. Ya está corregido: ahora arma la lista de recursos
  con `SECRET_ARN` + `DB_SECRET_ARN`. Como `DB_SECRET_ARN` lo escribe `07-rds.sh`,
  que corre **después**, hay que **re-ejecutar `03-secrets-iam.sh` después de
  `07-rds.sh`** (el script avisa si falta).
- **Contraseñas sembradas por defecto**: son **4**, no una (ver 4.5). Rotar las
  cuatro desde la pantalla de Usuarios apenas esté arriba.

### 4.7 API Gateway apunta a un Cloud Map equivocado

Bloqueante independiente de todo lo anterior: **hoy el API Gateway devuelve 503
en todas las rutas**, incluso con el backend sano.

```
GET https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/  → 503 {"message":"Service Unavailable"}
GET http://<ip-publica-de-la-task>:8000/                     → 200
```

Hay **dos servicios de Cloud Map llamados `medchain-backend`**:

| Servicio | Quién lo usa | Instancias |
|---|---|---|
| `srv-lmoij4mfyg2tbvu2` | **ECS** (auto-registro vía `serviceRegistries`) | la task viva |
| `srv-ndgsq7branjc4pek` | **API Gateway** (integración `41deb2p`) | `backend-task-1` → IP muerta |

La causa está en `deploy/05-api-gateway.sh`: resolvía el ARN con
`list-services` **sin filtrar por namespace** y sin tomar `| [0]`, así que con
servicios homónimos elegía el equivocado. Ya está corregido (filtra por
`NAMESPACE_ID` y valida contra el `registryArn` real del servicio ECS).

Arreglo sobre lo que ya está desplegado:

```bash
aws apigatewayv2 update-integration --api-id vl5nsf5jt5 --integration-id 41deb2p \
  --integration-uri arn:aws:servicediscovery:us-east-1:007072540405:service/srv-lmoij4mfyg2tbvu2 \
  --region us-east-1

aws servicediscovery deregister-instance --service-id srv-ndgsq7branjc4pek \
  --instance-id backend-task-1 --region us-east-1
```

---

## 5. Orden de ejecución recomendado

```
1. Backup de RDS (snapshot) y esperar a que termine            [4.5]
2. VPC peering + rutas + SG 8081; cerrar el 1433               [4.2]
3. Generar GATEWAY_AUTH_TOKEN y guardarlo en Secrets Manager   [4.1]
4. EC2: git pull, .env con el token, red de 3 orgs, deployCC,
   gateway arriba y /health en verde                           [4.4]
5. Completar deploy/.env.deploy con FABRIC_GATEWAY_URL,
   DB_SECRET_ARN y ENCRYPTION_SECRET_ARN                       [4.3]
6. Registrar la nueva task definition y update-service         [4.3, 4.6]
7. Repuntar API Gateway al Cloud Map correcto                  [4.7]
8. Push a `main` → CI (tests Go + Python) y deploy
   automático de backend, frontend y blockchain
9. Verificación end-to-end                                     [7]
10. Rotar las 4 contraseñas por defecto                        [4.5, 4.6]
```

Dos precedencias que importan:

- **4 antes de 6**: si el backend arranca sin gateway disponible, toda operación
  de prescripciones responde 503.
- **1 antes de 6**: la migración 007 corre sola al arrancar el contenedor
  (`db_bootstrap`), así que el snapshot tiene que estar **completo** antes de que
  se registre la task definition nueva. No hay downgrade.

Y una advertencia sobre el paso 8: si los pasos 2, 3 y 6 no están hechos, el
deploy vuelve a fallar por fail-fast y ECS lo revierte (sección 3.1).

---

## 6. Qué hace el CI/CD con estos cambios

**`ci.yml`** (en PRs y push a `desarrollo` o `main`) — jobs nuevos:
- `chaincode-tests`: `go mod tidy`, `go vet`, `go test` del chaincode
  (transiciones de estado, control por MSP, vectores de hash compartidos,
  guard-rail anti-`time.Now()` y cobertura de índices CouchDB).
- `gateway-build`: `go vet` + `go build` del puente.
- `backend-tests` levanta un Postgres real para correr `test_schema_drift.py`,
  que verifica que `sql/schema.sql` y las migraciones Alembic no se desincronicen.

**`deploy.yml`** (push a `main`):
- `deploy-blockchain` despliega en la EC2 la rama que disparó el workflow
  (`main` en push, o la elegida en *Run workflow*), en lugar de `desarrollo` fijo.
- Filtro de paths actualizado: `blockchain/**` → `chaincode/**` +
  `fabric-gateway-svc/**` + `fabric/**`.
- `deploy-blockchain` ya no es `continue-on-error` y ahora también rebuildea el
  gateway y valida `/health`.
- Corregido: la secuencia del chaincode se calculaba con `--name basic` (otro
  chaincode); ahora la autodetecta `deployChaincode.sh`.
- **Nuevo — `workflow_dispatch`**: se puede redesplegar a mano desde la pestaña
  Actions eligiendo por checkbox qué desplegar (backend / frontend / blockchain),
  sin necesidad de commitear. Útil tras recrear la red Fabric o rotar un secreto.
  En push no cambia nada: sigue mandando el filtro de paths.
- **Nuevo — detección de rollback**: `deploy-backend` guarda el ID del deployment
  que crea `update-service` y, después de `wait services-stable`, verifica que
  siga siendo el `PRIMARY` con `rolloutState=COMPLETED`. Si el circuit breaker de
  ECS revirtió, el job falla y vuelca los últimos eventos del servicio más los
  logs de la task detenida. Sin esto, un deploy revertido quedaba en verde
  (sección 3.1).

---

## 7. Verificación post-deploy

```bash
# 0. El deployment NO fue revertido por el circuit breaker
aws ecs describe-services --cluster medchain-cluster --services medchain-backend-svc \
  --region us-east-1 --query "services[0].deployments[?status=='PRIMARY'].[taskDefinition,rolloutState]"
#    esperado: la revision nueva + COMPLETED

# 1. Backend arriba y viendo la red
curl -s https://vl5nsf5jt5.execute-api.us-east-1.amazonaws.com/ | jq
#    esperado: "fabric_gateway": "ok"
#    El campo fabric_gateway es el discriminante: si NO aparece, esta corriendo
#    codigo pre-refactor (y si da 503, revisar 4.7 antes que Fabric).

# 2. Gateway y peers (desde la EC2, o por SSM)
curl -s --cacert fabric/network/gateway-tls/ca.crt https://localhost:8443/health | jq '.orgs'
#    esperado: prescriptor / auditor / prepaga en "ok"
```

**Resultado de la corrida del 18/08/2026**: 25/25 checks OK — API Gateway
enruta, el backend es el refactorizado y ve la red (`fabric_gateway: ok`),
login de los 4 roles, los 3 peers en verde, alta on-chain con TxID real,
`revision` → `aprobar`, 3 transacciones en el ledger, **`verify` → `valido:
true`**, cola paginada por bookmark, Alembic en `007` y RDS sin tablas
off-chain.

Checklist funcional en la UI:

1. **Login `superadmin`** → ve Usuarios y Salud del sistema; la pantalla de
   Salud muestra DB, modelo ML y los 3 peers en verde.
2. **Crear un usuario** con rol prescriptor y otro auditor; verificar que
   pueden loguearse.
3. **Login prescriptor** → alta de prescripción; la respuesta debe traer
   `estado: PENDIENTE_AUDITORIA`, un **TxID real de Fabric** y `payload_hash`.
4. **Login auditor** → la prescripción aparece en la cola; registrar
   `revisión` y luego `aprobar`; el detalle muestra los dos eventos encadenados
   con sus hashes.
5. **Trazabilidad** → buscar el código: historial con 3 transacciones y el chip
   "Cadena de hashes verificada".
6. **Paginación con más de una página**: dar de alta ~60 prescripciones y paginar
   la cola de auditoría con "cargar más". Es el caso que ejercita las rich queries
   con `sort` contra CouchDB; el flujo de una sola prescripción pasa igual aunque
   falten los índices, así que sin este paso el problema aparece recién en la demo.
7. **RDS limpia**: `\dt` no debe listar `prescriptions`, `audit_cases`,
   `dictamenes`, `corrections`, `prescription_outbox` ni `ledger_blocks`.

Prueba de la garantía de no adulteración (buena para la defensa): invocar el
chaincode desde el CLI apuntando a **un solo peer** debe fallar por política de
endorsement, y una `AuditPrescription` firmada como PrescriptorMSP debe ser
rechazada por control de acceso de MSP.

---

## 8. Riesgos conocidos

| Riesgo | Mitigación |
|---|---|
| Con endorsement `AND` de 3 orgs, un peer caído bloquea **todas** las escrituras | Limitación aceptada y documentada; visible en la pantalla de Salud y en `/health` |
| Alta síncrona: la latencia percibida sube (~2–4 s) | `BatchTimeout` bajado a 1s; la UI muestra "Registrando en blockchain…" |
| Todo Fabric corre en una sola EC2 (SPOF) | Aceptado para la tesis; el pipeline falla ruidosamente si la red no responde |
| Gateway en HTTP plano | **Resuelto (17/10/2026)**: el backend llama por `https://…:8443` y valida contra la CA del proyecto (sección 11). El HTTP 8081 se apagó y su regla se revocó (11.5) |
| Tramo API Gateway → tarea en HTTP y puerto 8000 abierto a Internet | **Resuelto (17/10/2026)**: SG autorreferenciado e integración con `tlsConfig` (sección 11) |
| Migración 007 irreversible | Snapshot previo de RDS (obligatorio, 4.5) |
| t3.large al límite de memoria | Plan B: t3.xlarge |
| Sesiones: `auth_tokens` en RDS ya soporta múltiples réplicas | Se puede subir `desiredCount` sin romper el login |
| **El timeout total de escritura (~138 s: 45 s × 3 reintentos + backoff) supera el idle timeout de API Gateway (29 s)**: el 503 diseñado llega al browser como 504 opaco | Pendiente. Bajar `_TIMEOUT_SECONDS`/`_MAX_RETRIES` en `backend/blockchain/fabric_client.py` para que el peor caso entre en 29 s |
| **Dos singletons de `FabricClient`** (`dependencies.py:37` vs `fabric_client.py:215`): la pantalla de Salud lee un circuit breaker distinto del que gobierna las escrituras | Pendiente. Unificar en una sola instancia; el diagnóstico del super admin puede mostrar "ok" con las escrituras cortadas |
| **Logout tarda hasta 60 s en propagarse** entre réplicas por el cache en RAM de `auth_service.py` | Aceptado con `desiredCount=1`; a revisar si se escala |
| La IP pública de la EC2 es dinámica y no hay Elastic IP | Con el peering se usa la IP privada; para SSH, resolverla con `describe-instances` (4.4) |

---

## 9. Inventario de la infraestructura (18/08/2026)

Recursos que hoy sostienen el sistema, con los IDs reales.

| Recurso | Identificador | Nota |
|---|---|---|
| VPC de la app | `vpc-0c98e7d7f299bf5e8` (`medchain-vpc`, 10.0.0.0/16) | ECS + RDS |
| VPC de Fabric | `vpc-09fcdbfb17d5cae13` (default, 172.31.0.0/16) | La EC2 vive acá |
| **VPC peering** | `pcx-040412e3bff5c43a4` | Rutas en `rtb-06535a6a07f86d8af` y `rtb-059dd8261a2ca0f17` |
| EC2 de Fabric | `i-0331b3fbeaadee294` (`t3.large`, IP privada `172.31.89.189`) | IP pública **dinámica**: resolverla con `describe-instances` |
| SG de Fabric | `sg-0c6d00bf321b64291` | 22 (mundo) y 8443 (`10.0.0.0/16`) |
| SG del backend | `sg-08518301fe0009809` | 8000 **solo desde sí mismo** (lo comparte el VPC Link) |
| Cluster / servicio ECS | `medchain-cluster` / `medchain-backend-svc` | Task definition `medchain-backend:7` (TLS en los dos tramos) |
| Cloud Map (en uso) | `srv-ty4v27ve53xropsy` (`medchain-backend-srv`) | Registros **SRV**: aporta `AWS_INSTANCE_PORT` |
| Cloud Map (obsoletos) | `srv-lmoij4mfyg2tbvu2`, `srv-ndgsq7branjc4pek` | Sin uso; se pueden borrar |
| API Gateway | `vl5nsf5jt5` + VPC Link `q6olhm` | Integración **`ma16yyi`** (HTTPS, `ServerNameToVerify=api-interno.medchain-pfi.com`). La integración HTTP original (`41deb2p`) se borró |
| CloudFront / S3 | `E3UXMQZNKANQDB` / `medchain-frontend-…-an` | Frontend. Alias `app.medchain-pfi.com` (ACM, TLS 1.2 mínimo) |
| Dominio | `medchain-pfi.com` (Route 53, zona `Z07647561HFTOSR51FM9`) | Renovación automática anual |
| Secreto TLS | `medchain/backend-tls` | `FABRIC_GATEWAY_CA_PEM`, `TLS_CERT_PEM`, `TLS_KEY_PEM` |
| RDS | `medchain-db` (PostgreSQL 16) | Alembic en `007` |
| Snapshot de rollback | `medchain-pre-007-20260818` | Previo a la 007 |
| Secretos | `medchain/auth-credentials`, `/database-credentials`, `/encryption-key`, `/github-token` | |
| Rol de la EC2 | `ec2-ssm-fabric` | SSM + CloudWatch + `AllowGitHubTokenRead` |

**Acceso de la EC2 al repo privado.** El repositorio es privado y la instancia
no tenía credenciales, lo que también rompía el job `deploy-blockchain`. Se
instaló un credential helper en `/usr/local/bin/git-credential-medchain`
(registrado con `git config --system credential.helper medchain`) que resuelve
el PAT desde `medchain/github-token` usando el instance role. **El token no
queda en disco ni viaja por los parámetros de SSM**, que quedan registrados en
el historial de comandos. Para rotarlo alcanza con `put-secret-value` sobre ese
secreto: no hay que tocar la instancia.

Además se instaló el **AWS CLI v2** en la EC2 (lo necesita el credential
helper) y se dejó Go accesible en el `PATH` de root vía symlinks en
`/usr/local/bin` más `/etc/profile.d/go.sh`, porque SSM corre como root y
`peer lifecycle chaincode package` necesita `go` para resolver el módulo.

---

## 10. Referencias

- Convención de hashing verificable: [HASHING.md](HASHING.md)
- Arquitectura de la red de 3 orgs: [02-arquitectura.md](02-arquitectura.md)
- Uso de los scripts de red: [03-uso.md](03-uso.md)
- Setup de la EC2: [04-aws-ec2-setup.md](04-aws-ec2-setup.md)
- Plan de implementación original: `~/.claude/plans/como-experto-en-ingenieria-curried-valley.md`

---

## 11. TLS en los tramos internos (17/10/2026)

Cierra la observación de que los datos de salud y las credenciales de sesión
viajaban en claro entre API Gateway y la tarea, y entre la tarea y el puente
Fabric, con el 8000 abierto a Internet.

### 11.1 Saltos y quién valida cada certificado

| Salto | Transporte | Certificado | Lo valida |
|---|---|---|---|
| Navegador → CloudFront | HTTPS 443, TLS ≥ 1.2 | ACM, `app.medchain-pfi.com` | El navegador |
| CloudFront → API Gateway | HTTPS 443 | AWS (`*.execute-api`) | CloudFront |
| API Gateway → VPC Link → tarea | **HTTPS 8000** | Let's Encrypt, `api-interno.medchain-pfi.com` | API Gateway (`tlsConfig.ServerNameToVerify`) |
| Tarea → RDS | TLS 5432 | RDS | psycopg2 (`verify-full`) |
| Tarea → puente Fabric | **HTTPS 8443** | CA propia del proyecto, SAN `IP:172.31.89.189` | `FabricClient`, solo contra `FABRIC_GATEWAY_CA_PEM` |
| Puente → peers | gRPC sobre TLS | TLS CA de cada org (cryptogen) | Fabric Gateway SDK |

**Por qué dos clases de certificado.** Un HTTP API de API Gateway solo cifra
hacia una integración privada si el backend presenta un certificado de una CA
**pública**: la opción que acepta CAs privadas (`insecureSkipVerification`)
existe solo en REST APIs. De ahí el dominio y Let's Encrypt. El tramo hacia el
puente no tiene esa restricción porque el cliente es nuestro, así que usa una CA
propia que no depende de terceros.

**RSA a propósito.** API Gateway confía en ISRG Root X1 (RSA) y no en ISRG Root
X2. La cadena emitida es hoja → YR1 → Root YR, con Root YR firmada por ISRG
Root X1. Un certificado ECDSA no validaría.

### 11.2 Exposición del puerto 8000

`sg-08518301fe0009809` admite el 8000 **solo desde sí mismo**. Funciona porque
el VPC Link `q6olhm` se creó con ese mismo SG. La tarea sigue teniendo IP
pública (`assignPublicIp=ENABLED`), que necesita para salir a ECR, Secrets
Manager y CloudWatch sin NAT, pero ninguna regla admite tráfico entrante desde
Internet. Verificado: el acceso directo a la IP pública da timeout.

### 11.3 Renovación del certificado del backend

`.github/workflows/renew-backend-cert.yml` corre los lunes, también cuando
cambia su propio archivo y a mano (`workflow_dispatch` con `force`). Renueva si
faltan menos de 30 días: hace el desafío DNS-01 en Route 53, guarda
`TLS_CERT_PEM`/`TLS_KEY_PEM` en `medchain/backend-tls` **sin pisar** las otras
claves del secreto y fuerza un redeploy si la task definition los consume.

Si el workflow deja de correr, el certificado vence a los 90 días y API Gateway
empieza a responder 503 en todas las rutas. Para diagnosticarlo, mirar
`openssl x509 -enddate` del certificado guardado en el secreto.

### 11.4 Certificado del puente Fabric

`fabric/scripts/gateway-tls.sh` genera en `fabric/network/gateway-tls/`
(gitignored, fuera de `organizations/`) una CA de 10 años y un certificado de
servidor de 2 años. Hay que reemitirlo en dos casos:

- **Vencimiento** (10/2028): `./fabric/scripts/gateway-tls.sh --renew` en la
  EC2 y reiniciar el gateway. La CA no cambia, así que el backend no se toca.
- **Cambio de IP privada de la EC2**: el mismo `--renew`, más actualizar
  `FABRIC_GATEWAY_URL` en una nueva revisión de la task definition.

`network.sh up` llama al script si falta el certificado. Sin certificado el
gateway no arranca.

### 11.5 Endurecimiento (aplicado el 17/10/2026)

Ya no queda ningún camino en claro:

- El gateway sirve **solo HTTPS**: `LISTEN_ADDR` vale `off` por defecto y el
  compose ya no publica el 8081. Para desarrollo local se puede habilitar HTTP
  con `GATEWAY_LISTEN_ADDR=:8081` en `fabric/network/.env` (y publicando el
  puerto), nunca en la EC2.
- La regla del 8081 se revocó en `sg-0c6d00bf321b64291`.
- El smoke test de `deploy.yml` consulta `https://localhost:8443/health` con
  `--cacert`.
- `config.py` rechaza en producción una `FABRIC_GATEWAY_URL` que no sea
  `https://`.
- La integración HTTP `41deb2p` se borró. Para un rollback hay que recrearla
  (ver el plan).

El plan completo y el rollback paso a paso están en
`deploy/rollback/PLAN-TLS-Y-ROLLBACK.md` (local, gitignored).
