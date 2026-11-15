# Despliegue en AWS — Paso a paso desde la consola web

Guia completa para desplegar MedChain AI en AWS usando la consola web (Management Console).

**Arquitectura final:**

- Frontend (React) en **S3 + CloudFront**
- Backend (FastAPI) en **ECS Fargate** expuesto por **API Gateway HTTP API**
- Blockchain (Fabric) en **EC2 dedicada** (maquina separada)

**Costo estimado (trafico bajo de PFI):** ~USD 12-15/mes + EC2 Fabric ~USD 2/dia encendida.

---

## Prerequisitos

1. Cuenta de AWS activa (puede ser AWS Academy / educativa).
2. Instalar **AWS CLI v2** en tu maquina local:
  - Descargar de [https://aws.amazon.com/cli/](https://aws.amazon.com/cli/)
  - Ejecutar `aws configure` y poner tu Access Key, Secret Key, region `us-east-1`.
3. **Docker Desktop** corriendo en tu maquina (para construir la imagen).
4. **Node.js + npm** instalados (para el build del frontend).

---

## PASO 1: Crear la VPC (Red privada virtual)

> Servicio: **VPC** (buscar "VPC" en la barra de busqueda de AWS)

### 1.1 Crear la VPC

1. Ir a **VPC > Your VPCs > Create VPC**
2. Configurar:
  - **Resources to create:** VPC and more
  - **Name tag auto-generation:** `medchain`
  - **IPv4 CIDR block:** `10.0.0.0/16`
  - **Number of Availability Zones:** `2`
  - **Number of public subnets:** `2`
  - **Number of private subnets:** `0`
  - **NAT gateways:** `None` (ahorramos ~USD 32/mes)
  - **VPC endpoints:** `None`
  - **Enable DNS hostnames:** Si
  - **Enable DNS resolution:** Si
3. Click **Create VPC**
4. Esperar a que se creen todos los recursos (VPC, subredes, IGW, route tables)
5. **Anotar** los IDs:
  - VPC ID: `vpc-xxxx`
  - Subnet publica AZ-a: `subnet-xxxx`
  - Subnet publica AZ-b: `subnet-xxxx`

### 1.2 Crear Security Group para ECS

1. Ir a **VPC > Security Groups > Create security group**
2. Configurar:
  - **Security group name:** `medchain-ecs-sg`
  - **Description:** `SG para tareas Fargate del backend`
  - **VPC:** seleccionar `medchain-vpc`
3. **Inbound rules > Add rule:**
  - Type: `Custom TCP`
  - Port range: `8000`
  - Source: `Anywhere-IPv4` (0.0.0.0/0)
4. **Outbound rules:** dejar la regla default (All traffic, 0.0.0.0/0)
5. Click **Create security group**
6. **Anotar** el Security Group ID: `sg-xxxx`

---

## PASO 2: Crear repositorio ECR y subir la imagen Docker

> Servicio: **ECR** (buscar "Elastic Container Registry")

### 2.1 Crear repositorio

1. Ir a **ECR > Repositories > Create repository**
2. Configurar:
  - **Visibility:** Private
  - **Repository name:** `medchain-backendmedchain-backend`
3. Click **Create repository**
4. Click en el repositorio creado y luego **View push commands** (boton arriba a la derecha)

### 2.2 Construir y subir la imagen (desde tu terminal local)

AWS te muestra 4 comandos. Ejecutalos desde la raiz del proyecto (`PFI-Proyecto-Final/`):

```bash
# 1. Login en ECR (copiar el comando exacto que te da AWS)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin TU_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 2. Construir la imagen
docker build -t medchain-backend .

# 3. Taguear
docker tag medchain-backend:latest TU_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest

# 4. Subir
docker push TU_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest
```

> **Nota Windows:** si estas en PowerShell, los comandos son los mismos. Si Docker Desktop no esta corriendo, inicialo primero.

1. Verificar en la consola que la imagen aparece en el repositorio.
2. **Anotar** el Image URI: `TU_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest`

---

## PASO 3: Guardar credenciales en Secrets Manager

> Servicio: **Secrets Manager** (buscar "Secrets Manager")

1. Ir a **Secrets Manager > Store a new secret**
2. Configurar:
  - **Secret type:** Other type of secret
  - **Key/value pairs** (agregar 3 filas):

    | Key                 | Value           |
    | ------------------- | --------------- |
    | `AUTH_USERNAME`     | `admin`         |
    | `AUTH_PASSWORD`     | `admin123`      |
    | `AUTH_DISPLAY_NAME` | `Administrador` |

  - **Encryption key:** dejar `aws/secretsmanager` (default)
3. Click **Next**
4. **Secret name:** `medchain/auth-credentials`
5. Click **Next > Next > Store**
6. Click en el secreto creado y **anotar** el ARN completo: `arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:medchain/auth-credentials-XXXXXX`

---

## PASO 4: Crear roles IAM

> Servicio: **IAM** (buscar "IAM")

### 4.1 Execution Role (para que ECS pueda bajar la imagen y leer secrets)

1. Ir a **IAM > Roles > Create role**
2. **Trusted entity type:** AWS service
3. **Use case:** Elastic Container Service > Elastic Container Service Task
4. Click **Next**
5. Buscar y marcar: `AmazonECSTaskExecutionRolePolicy`
6. Click **Next**
7. **Role name:** `medchain-ecs-execution-role`
8. Click **Create role**

Ahora agregar permiso para leer el secreto:

1. Click en el rol recien creado
2. **Add permissions > Create inline policy**
3. Cambiar a **JSON** y pegar:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "ARN_DEL_SECRETO_DEL_PASO_3"
  }]
}
```

1. **Policy name:** `medchain-read-secrets`
2. Click **Create policy**
3. **Anotar** el ARN del rol: `arn:aws:iam::ACCOUNT:role/medchain-ecs-execution-role`

### 4.2 Task Role (permisos de la app, vacio por ahora)

1. **IAM > Roles > Create role**
2. **Trusted entity type:** AWS service
3. **Use case:** Elastic Container Service > Elastic Container Service Task
4. Click **Next > Next** (sin agregar policies)
5. **Role name:** `medchain-ecs-task-role`
6. Click **Create role**

---

## PASO 5: Crear cluster ECS y servicio Fargate

> Servicio: **ECS** (buscar "Elastic Container Service")

### 5.1 Crear namespace en Cloud Map

> Servicio: **Cloud Map** (buscar "Cloud Map")

1. Ir a **Cloud Map > Create namespace**
2. Configurar:
  - **Namespace name:** `medchain.local`
  - **Namespace type:** HTTP
3. Click **Create namespace**
4. **Anotar** el Namespace ID

### 5.2 Crear cluster ECS

1. Ir a **ECS > Clusters > Create cluster**
2. Configurar:
  - **Cluster name:** `medchain-cluster`
  - **Infrastructure:** AWS Fargate (solo Fargate, desmarcar EC2 si esta marcado)
3. Click **Create**

### 5.3 Crear Task Definition

1. Ir a **ECS > Task definitions > Create new task definition**
2. Configurar:

**Task definition configuration:**

- **Task definition family:** `medchain-backend`
- **Launch type:** AWS Fargate
- **OS/Arch:** Linux/X86_64
- **Task size:** CPU = `0.25 vCPU`, Memory = `0.5 GB`
- **Task role:** `medchain-ecs-task-role`
- **Task execution role:** `medchain-ecs-execution-role`

**Container - 1:**

- **Name:** `medchain-backend`
- **Image URI:** `TU_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest`
- **Essential container:** Yes
- **Port mappings:** Container port = `8000`, Protocol = `TCP`

**Environment variables (expandir seccion):**

Elegir **ValueFrom** (no Value) para cada una:


| Key                 | Value from                            |
| ------------------- | ------------------------------------- |
| `AUTH_USERNAME`     | `ARN_DEL_SECRETO:AUTH_USERNAME::`     |
| `AUTH_PASSWORD`     | `ARN_DEL_SECRETO:AUTH_PASSWORD::`     |
| `AUTH_DISPLAY_NAME` | `ARN_DEL_SECRETO:AUTH_DISPLAY_NAME::` |


> Formato exacto del ValueFrom: `arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:medchain/auth-credentials-XXXXXX:AUTH_USERNAME::`

**Log collection:**

- Marcar **Use log collection**
- **Log driver:** `awslogs`
- Dejar los valores default (crea un log group automaticamente)

**Health check (en la seccion del container):**

- Command: `CMD-SHELL, python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"`
- Interval: `30`
- Timeout: `5`
- Start period: `15`
- Retries: `3`

1. Click **Create**

### 5.4 Crear servicio

1. Ir a **ECS > Clusters > medchain-cluster > Services > Create**
2. Configurar:

**Environment:**

- **Launch type:** Fargate
- **Platform version:** LATEST

**Deployment configuration:**

- **Application type:** Service
- **Task definition:** `medchain-backend` (seleccionar la ultima revision)
- **Service name:** `medchain-backend-svc`
- **Desired tasks:** `1`

**Networking:**

- **VPC:** `medchain-vpc`
- **Subnets:** seleccionar las 2 subredes publicas
- **Security group:** seleccionar `medchain-ecs-sg` (remover el default)
- **Public IP:** `Turned on`

**Service discovery (expandir):**

- Marcar **Use Service Discovery**
- **Namespace:** `medchain.local`
- **Service discovery name:** `medchain-backend`
- **DNS record type:** A
- **TTL:** 10

1. Click **Create**
2. Esperar 2-3 minutos hasta que la task pase a estado **RUNNING**

**Verificar:**

- Ir a la task corriendo, buscar la **Public IP**
- En el navegador: `http://PUBLIC_IP:8000/` deberia devolver `{"status":"ok","service":"MedChain AI"}`
- Probar: `http://PUBLIC_IP:8000/docs` para ver Swagger

---

## PASO 6: Crear API Gateway HTTP API + VPC Link

> Servicio: **API Gateway** (buscar "API Gateway")

### 6.1 Crear VPC Link

1. Ir a **API Gateway > VPC links (panel izquierdo, abajo) > Create VPC link**
2. Elegir **VPC link for HTTP APIs**
3. Configurar:
  - **Name:** `medchain-vpclink`
  - **VPC:** `medchain-vpc`
  - **Subnets:** las 2 publicas
  - **Security groups:** `medchain-ecs-sg`
4. Click **Create**
5. Esperar hasta que el status sea **Available** (puede tardar 2-5 minutos)

### 6.2 Crear HTTP API

1. Ir a **API Gateway > APIs > Create API**
2. Elegir **HTTP API > Build**
3. **API name:** `medchain-api`
4. Click **Next** (skip integrations por ahora) > **Next** > **Next** > **Create**

### 6.3 Agregar integracion y ruta

1. Click en `medchain-api` > **Develop > Integrations > Create**
2. Configurar:
  - **Attach this integration to a route:** No, skip
  - **Integration type:** Private resource
  - **Integration details:** Select manually
  - **Target service:** Cloud Map
  - **Namespace:** `medchain.local`
  - **Service:** `medchain-backend`
  - **VPC link:** `medchain-vpclink`
3. Click **Create**
4. **Anotar** el Integration ID

Ahora crear las rutas:

1. Ir a **Routes > Create**
2. **Method:** ANY, **Path:** `/{proxy+}`
3. Click **Create**
4. Click en la ruta `ANY /{proxy+}` > **Attach integration** > seleccionar la integracion creada
5. Repetir para ruta `ANY /` (misma integracion)

### 6.4 Obtener la URL

1. Ir a **API Gateway > APIs > medchain-api**
2. En el panel lateral, la **Invoke URL** aparece arriba (algo como `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`)
3. **Anotar** esta URL
4. Probar en navegador: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/` deberia devolver el health check

---

## PASO 7: Subir frontend a S3

> Servicio: **S3** (buscar "S3")

### 7.1 Crear bucket

1. Ir a **S3 > Create bucket**
2. Configurar:
  - **Bucket name:** `medchain-frontend-TUNUMERODECUENTA` (debe ser unico global)
  - **Region:** `us-east-1`
  - **Block all public access:** DEJAR ACTIVADO (el acceso va por CloudFront, no directo)
3. Click **Create bucket**

### 7.2 Subir el build (desde tu terminal local)

```bash
cd frontend
npm run build

# Subir a S3
aws s3 sync dist/ s3://medchain-frontend-TUNUMERODECUENTA/ --delete
```

Verificar en la consola S3 que los archivos aparecen (index.html, assets/, etc.)

---

## PASO 8: Crear CloudFront (CDN)

> Servicio: **CloudFront** (buscar "CloudFront")

### 8.1 Crear distribucion

1. Ir a **CloudFront > Distributions > Create distribution**

**Origin 1 (S3 — SPA):**

- **Origin domain:** seleccionar el bucket S3 (`medchain-frontend-TUNUMERODECUENTA.s3.us-east-1.amazonaws.com`)
- **Origin access:** Origin access control settings (recommended)
- Click **Create new OAC** > dejar defaults > **Create**
- **Origin path:** dejar vacio

**Default cache behavior:**

- **Viewer protocol policy:** Redirect HTTP to HTTPS
- **Allowed HTTP methods:** GET, HEAD
- **Cache policy:** CachingOptimized
- **Compress objects automatically:** Yes

1. **Agregar un segundo origin** (scroll abajo o despues de crear):

Primero crear la distribucion con el S3 y despues agregar el segundo origin:

1. **Web Application Firewall:** Do not enable
2. **Default root object:** `index.html`
3. **Price class:** Use only North America and Europe (mas barato)
4. Click **Create distribution**

### 8.2 Agregar origin del API Gateway

1. Ir a la distribucion creada > **Origins > Create origin**
2. Configurar:
  - **Origin domain:** pegar el dominio del API Gateway SIN el `https://` (ej: `xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`)
  - **Protocol:** HTTPS only
  - **Origin name:** `api-gateway`
3. Click **Create origin**

### 8.3 Crear behavior para /api/*

1. Ir a **Behaviors > Create behavior**
2. Configurar:
  - **Path pattern:** `/api/`*
  - **Origin:** `api-gateway` (el que recien creaste)
  - **Viewer protocol policy:** Redirect HTTP to HTTPS
  - **Allowed HTTP methods:** GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
  - **Cache policy:** CachingDisabled
  - **Origin request policy:** AllViewerExceptHostHeader
3. Click **Create behavior**

### 8.4 Configurar fallback SPA (para BrowserRouter)

1. Ir a **Error pages > Create custom error response**
2. Crear para error 403:
  - **HTTP error code:** 403
  - **Customize error response:** Yes
  - **Response page path:** `/index.html`
  - **HTTP response code:** 200
3. Repetir para error 404 (misma config)

### 8.5 Actualizar la bucket policy de S3

Cuando creaste la distribucion con OAC, CloudFront te muestra un banner azul que dice **"Copy policy"**. Si no lo ves:

1. Ir a la distribucion > **Origins** > click en el origin S3 > **Edit**
2. Arriba aparece el banner con **Copy policy**
3. Copiar la policy
4. Ir a **S3 > tu bucket > Permissions > Bucket policy > Edit**
5. Pegar la policy y **Save changes**

### 8.6 Obtener la URL final

1. Ir a **CloudFront > tu distribucion**
2. Copiar el **Distribution domain name**: `dXXXXXXXXXX.cloudfront.net`
3. Esperar 5-15 minutos hasta que el Status sea **Deployed**
4. Abrir en el navegador: `https://dXXXXXXXXXX.cloudfront.net`

**Esta es la URL publica de tu aplicacion.**

---

## PASO 9: EC2 para Blockchain (maquina separada)

> Servicio: **EC2** (buscar "EC2")

Seguir la guia existente en [04-aws-ec2-setup.md](04-aws-ec2-setup.md), con estos datos:

### 9.1 Lanzar instancia

1. Ir a **EC2 > Launch instances**
2. Configurar:
  - **Name:** `pfi-fabric`
  - **AMI:** Ubuntu Server 24.04 LTS (64-bit x86)
  - **Instance type:** `t3.large` (2 vCPU, 8 GB RAM)
  - **Key pair:** crear uno nuevo o usar existente
  - **Storage:** 30 GB gp3
3. **Network settings > Edit:**
  - **VPC:** puede ser la misma `medchain-vpc` o la default
  - **Auto-assign public IP:** Enable
  - **Security group:** crear uno nuevo
    - Solo regla SSH (port 22) desde **My IP**
    - NO abrir puertos de Fabric (7050/7051/9051) a internet
4. Click **Launch instance**

### 9.2 Conectar y provisionar

```bash
ssh -i tu-clave.pem ubuntu@IP_PUBLICA_EC2

# Clonar el repo
git clone https://github.com/fcores/PFI-Proyecto-Final.git
cd PFI-Proyecto-Final/fabric/scripts

# Provisionar (Docker + Go)
chmod +x bootstrap.sh
./bootstrap.sh

# Cerrar sesion y volver a entrar (para que docker funcione sin sudo)
exit
ssh -i tu-clave.pem ubuntu@IP_PUBLICA_EC2

# Levantar la red
cd PFI-Proyecto-Final/fabric
./network.sh install        # Descargar binarios e imagenes (una sola vez, tarda ~5 min)
./network.sh up             # Generar cripto + levantar contenedores
./network.sh createChannel  # Crear canal mychannel + unir peers
./network.sh deployCC       # Desplegar chaincode + prueba
```

### 9.3 Verificar

```bash
docker ps
# Deberias ver: orderer.example.com, peer0.org1.example.com, peer0.org2.example.com, cli
```

### 9.4 Apagar para ahorrar

Cuando no la uses: **EC2 > Instances > seleccionar pfi-fabric > Instance state > Stop instance**
(~USD 2/dia encendida, USD 0 detenida excepto disco ~USD 2.4/mes)

---

## PASO 10: Verificacion final

Abrir `https://dXXXXXXXXXX.cloudfront.net` en el navegador:

1. **Login:** usuario `admin`, password `admin123` -> debe ingresar correctamente
2. **Alta de prescripcion:** completar el formulario -> debe mostrar resultado de validacion y hash de blockchain
3. **Historial:** ir a historial de prescripciones -> debe aparecer la prescripcion creada
4. **Trazabilidad:** ir a trazabilidad -> debe mostrar los bloques del ledger
5. **Swagger:** abrir `https://dXXXXXXXXXX.cloudfront.net/api/docs` -> documentacion interactiva (nota: puede no funcionar por el proxy, en ese caso usar el endpoint directo de API Gateway)

---

## Resumen de URLs


| Recurso               | URL                                                           |
| --------------------- | ------------------------------------------------------------- |
| App (usuario final)   | `https://dXXXXXXXXXX.cloudfront.net`                          |
| API Gateway (directo) | `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`      |
| Health check          | `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/`     |
| Swagger               | `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/docs` |
| EC2 Fabric (SSH)      | `ssh -i clave.pem ubuntu@IP_EC2`                              |


---

## Resumen de costos mensuales (trafico bajo)


| Servicio                                 | Costo aproximado          |
| ---------------------------------------- | ------------------------- |
| ECS Fargate (0.25 vCPU, 0.5 GB, 24x7)    | ~USD 9-10                 |
| API Gateway HTTP API                     | ~centavos                 |
| CloudFront + S3                          | ~centavos                 |
| ECR (almacenamiento imagen)              | ~centavos                 |
| Secrets Manager (3 secrets)              | ~USD 1.20                 |
| EC2 t3.large (Fabric, si esta encendida) | ~USD 60/mes (o USD 2/dia) |
| **Total sin EC2 encendida**              | **~USD 12**               |
| **Total con EC2 24x7**                   | **~USD 72**               |


> **Tip:** apagar la EC2 de Fabric cuando no la uses reduce el costo a ~USD 12-15/mes.

---

## Troubleshooting comun


| Problema                               | Solucion                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------- |
| Task en ECS no arranca                 | Revisar logs en CloudWatch > Log groups > /ecs/medchain-backend                    |
| 503 en API Gateway                     | El VPC Link puede no estar listo, esperar 2-5 min. O la task no esta RUNNING       |
| 403 en CloudFront al acceder al SPA    | Falta la bucket policy con el OAC. Copiarla del banner de CloudFront               |
| Login devuelve 404                     | Verificar que el behavior `/api/*` en CloudFront apunta al origin del API Gateway  |
| Pagina en blanco al refrescar una ruta | Faltan los custom error responses (403/404 -> /index.html) en CloudFront           |
| `docker push` falla                    | Verificar que hiciste `aws ecr get-login-password` y Docker Desktop esta corriendo |
| EC2 Fabric: `network.sh up` falla      | Verificar que hiciste logout/login despues de bootstrap.sh (grupo docker)          |


