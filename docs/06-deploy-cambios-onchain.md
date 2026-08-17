# 06 — Deploy en AWS de los cambios on-chain

Documento de handoff del refactor **"prescripciones 100% on-chain + red de 3
organizaciones + 4 roles"** (agosto 2026). Cubre qué cambió, qué quedó
verificado y **qué falta hacer en AWS** para dejarlo funcionando.

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
| `chaincode/prescription-contract/` | Reescrito: asset completo, máquina de estados, control por MSP, hashing encadenado, rich queries paginadas + tests Go |
| `fabric-gateway-svc/` | De stub a puente real (SDK, 3 identidades, auth por token, mapeo de errores) + Dockerfile |
| `fabric/` | 3 orgs + CouchDB, política de endorsement explícita, `.env.example`, scripts actualizados |
| `backend/` | Prescripciones/auditoría contra Fabric; se eliminan ledger, outbox y repos off-chain; módulo de usuarios; Argon2id; sesiones persistentes |
| `sql/` + `alembic/` | Migración **006** (rol `super_admin` + `auth_tokens`) y **007** (DROP de las 6 tablas off-chain) |
| `frontend/` | 4 roles, gestión de usuarios, salud del sistema, cola de auditoría nueva, paginación por bookmark, trazabilidad desde Fabric |
| `.github/workflows/` | CI con jobs Go; deploy de blockchain sin `continue-on-error`, con rebuild del gateway y smoke test |
| `deploy/04-ecs-cluster.sh` | Task definition con `FABRIC_GATEWAY_URL` + `GATEWAY_AUTH_TOKEN` |

**Eliminados**: `blockchain/` (contrato legacy con PHI en claro),
`chaincode/asset-transfer-basic/`, `backend/services/ledger_service.py`,
`backend/blockchain/outbox_worker.py`, `backend/repositories/{prescription,audit,ledger}_repo.py`,
`sql/{prescriptions,audit,ledger}.sql`, `frontend/src/api/ledger.js`.

---

## 2. Estado: qué está verificado y qué no

### Verificado localmente

- `pytest`: **52 tests OK** (fake del chaincode con la misma semántica, vectores de hash compartidos Python↔Go, flujo completo de auditoría, ABM de usuarios, migración de passwords).
- `ruff` y `black` limpios sobre `backend/` y `tests/`.
- La app FastAPI levanta y expone sus 26 rutas.
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

| # | Tarea | Dónde | Bloqueante |
|---|---|---|---|
| 1 | Agregar `GATEWAY_AUTH_TOKEN` al secreto de Secrets Manager | Secrets Manager | Sí |
| 2 | Resolver la conectividad ECS ↔ EC2:8081 | VPC / SG | Sí |
| 3 | Registrar nueva revisión de la task definition con las env vars nuevas | ECS | Sí |
| 4 | Rehacer la red Fabric con 3 orgs + levantar el gateway | EC2 | Sí |
| 5 | Backup de la RDS antes de la migración 007 (borra prescripciones) | RDS | Recomendado |
| 6 | Agregar `ENCRYPTION_SECRET_ARN` a la task definition (deuda previa) | ECS | Recomendado |
| 7 | Cambiar la contraseña del `superadmin` sembrado | App | Recomendado |

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

### 4.2 Conectividad ECS ↔ EC2 (el punto más delicado)

**El problema**: las tasks ECS corren en la VPC `medchain-vpc` (`10.0.0.0/16`,
creada por `01-vpc-network.sh`) con `assignPublicIp=ENABLED`, mientras que la
EC2 de Fabric (`i-0331b3fbeaadee294`, Elastic IP `34.199.204.55`) **no la crea
ningún script del repo** y vive en otra VPC. Además, el gateway habla **HTTP
plano** en el 8081.

Consecuencias: no se puede autorizar por *security group de origen* entre VPCs
distintas, y la IP pública de salida de las tasks cambia en cada despliegue.

**Opciones** (ordenadas por recomendación):

| Opción | Trabajo | Resultado |
|---|---|---|
| **A. Mover la EC2 a `medchain-vpc`** (recomendada) | Medio: recrear la instancia en una subred pública de la VPC | `FABRIC_GATEWAY_URL=http://<ip-privada>:8081`, regla de SG con origen = `SG_ECS`, tráfico nunca sale a internet. Como la red Fabric hay que rehacerla igual (sección 4.4), el costo extra es bajo |
| **B. VPC peering** entre `medchain-vpc` y la VPC de la EC2 | Medio: peering + rutas + SG | Mismo resultado que A sin recrear la instancia |
| **C. Elastic IP pública + token** | Bajo | `FABRIC_GATEWAY_URL=http://34.199.204.55:8081` y abrir el 8081 en el SG. **Solo aceptable como demo**: expone el puerto a internet y el token viaja sin TLS |

Si por tiempo se elige **C**, dejarlo documentado como limitación y al menos
restringir el SG a los rangos de IP desde los que se pruebe.

Regla de SG para las opciones A/B:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0c6d00bf321b64291 \
  --protocol tcp --port 8081 \
  --source-group <SG_ECS> \
  --region us-east-1
```

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
   además ahora **falla si `FABRIC_GATEWAY_URL` no está definida**.

3. El health check del contenedor se ajustó a `timeout 10s` / `startPeriod 90s`
   porque `/` ahora consulta el gateway (con timeout propio de 2s). Si se
   registra la task def a mano, aplicar esos valores.

> **Fail-fast**: con `ENVIRONMENT=production`, el backend **no arranca** sin
> `DATABASE_URL`, `FABRIC_GATEWAY_URL` y `GATEWAY_AUTH_TOKEN`. Si falta alguna,
> la task entra en crash loop y `aws ecs wait services-stable` deja el pipeline
> en rojo (comportamiento intencional).

### 4.4 EC2 — rehacer la red Fabric y levantar el gateway

El material criptográfico cambia por completo (3 organizaciones nuevas con
dominios nuevos), así que **no hay upgrade incremental**: se baja la red y se
levanta de cero. Los datos de demo previos en el ledger se pierden.

```bash
ssh -i mi-key.pem ubuntu@34.199.204.55
cd ~/PFI-Proyecto-Final
git fetch origin desarrollo && git checkout desarrollo && git pull

cd fabric
cp network/.env.example network/.env
# Editar network/.env:
#   GATEWAY_AUTH_TOKEN=<el mismo token de Secrets Manager (4.1)>
#   COUCHDB_USER / COUCHDB_PASSWORD

./network.sh down            # limpia la red vieja de 2 orgs
./network.sh up              # genera cripto de las 3 orgs + peers + CouchDB + gateway
./network.sh createChannel   # une orderer y los 3 peers a mychannel
./network.sh deployCC        # instala/aprueba/commitea con la política AND

curl -s localhost:8081/health | jq   # las 3 orgs deben responder "ok"
```

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

> **Backup previo recomendado** (007 es irreversible y las prescripciones
> existentes no se migran a Fabric):
>
> ```bash
> aws rds create-db-snapshot --db-instance-identifier <instancia> \
>   --db-snapshot-identifier medchain-pre-007-$(date +%Y%m%d) --region us-east-1
> ```
>
> Si hiciera falta conservar las prescripciones de demo, hay que escribir un
> script de backfill que las recree vía el gateway **antes** de aplicar 007
> (no está implementado).

Al primer arranque con base disponible, `AuthService._seed_users()` siembra
`superadmin / super123` (además de admin, prescriptor y auditor si no existen).

### 4.6 Deuda previa que conviene cerrar en el mismo cambio

- **`ENCRYPTION_SECRET_ARN` no está en la task definition**: hoy, en producción,
  el cifrado de PHI de pacientes no tiene clave maestra de Secrets Manager. Ya
  que hay que registrar una revisión nueva (4.3), es el momento de agregarlo.
- **Contraseñas sembradas por defecto** (`superadmin/super123`, `admin/admin123`,
  etc.): cambiarlas desde la pantalla de Usuarios apenas esté arriba.
- **Permiso `GetSecretValue` sobre `DB_SECRET_ARN`**: verificar que el execution
  role lo cubra (la policy creada por `03-secrets-iam.sh` solo incluye
  `SECRET_ARN`).

---

## 5. Orden de ejecución recomendado

```
1. Backup de RDS (snapshot)                                    [4.5]
2. Generar GATEWAY_AUTH_TOKEN y guardarlo en Secrets Manager   [4.1]
3. Resolver conectividad ECS ↔ EC2 y anotar la URL final       [4.2]
4. EC2: git pull, .env con el token, red de 3 orgs, deployCC,
   gateway arriba y /health en verde                           [4.4]
5. Registrar la nueva task definition (FABRIC_GATEWAY_URL,
   GATEWAY_AUTH_TOKEN, ENCRYPTION_SECRET_ARN) y update-service  [4.3, 4.6]
6. Push a `desarrollo` → CI (tests Go + Python) y deploy
   automático de backend, frontend y blockchain
7. Verificación end-to-end                                     [7]
8. Cambiar contraseñas por defecto                             [4.6]
```

El paso 4 va **antes** del 5 a propósito: si el backend arranca sin gateway
disponible, toda operación de prescripciones responde 503.

---

## 6. Qué hace el CI/CD con estos cambios

**`ci.yml`** (en PRs y push a `desarrollo`) — jobs nuevos:
- `chaincode-tests`: `go mod tidy`, `go vet`, `go test` del chaincode
  (transiciones de estado, control por MSP, vectores de hash compartidos y
  guard-rail anti-`time.Now()`).
- `gateway-build`: `go vet` + `go build` del puente.

**`deploy.yml`** (push a `desarrollo`):
- Filtro de paths actualizado: `blockchain/**` → `chaincode/**` +
  `fabric-gateway-svc/**`.
- `deploy-blockchain` ya no es `continue-on-error` y ahora también rebuildea el
  gateway y valida `/health`.
- Corregido: la secuencia del chaincode se calculaba con `--name basic` (otro
  chaincode); ahora la autodetecta `deployChaincode.sh`.

---

## 7. Verificación post-deploy

```bash
# 1. Backend arriba y viendo la red
curl -s https://<cloudfront>/api/../ | jq        # o el endpoint raíz del API GW
#    esperado: "fabric_gateway": "ok"

# 2. Gateway y peers (desde la EC2)
curl -s localhost:8081/health | jq '.orgs'
#    esperado: prescriptor / auditor / prepaga en "ok"
```

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
6. **RDS limpia**: `\dt` no debe listar `prescriptions`, `audit_cases`,
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
| Gateway en HTTP plano | Resolver con la opción A/B de 4.2 (tráfico privado) o poner TLS |
| Migración 007 irreversible | Snapshot previo de RDS |
| t3.large al límite de memoria | Plan B: t3.xlarge |
| Sesiones: `auth_tokens` en RDS ya soporta múltiples réplicas | Se puede subir `desiredCount` sin romper el login |

---

## 9. Referencias

- Convención de hashing verificable: [HASHING.md](HASHING.md)
- Arquitectura de la red de 3 orgs: [02-arquitectura.md](02-arquitectura.md)
- Uso de los scripts de red: [03-uso.md](03-uso.md)
- Setup de la EC2: [04-aws-ec2-setup.md](04-aws-ec2-setup.md)
- Plan de implementación original: `~/.claude/plans/como-experto-en-ingenieria-curried-valley.md`
