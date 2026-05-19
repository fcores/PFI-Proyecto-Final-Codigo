# Arquitectura Paso a Paso - Swiss Empadronamiento + Blockchain

## Tabla de contenidos

1. [Vision general del proyecto](#1-vision-general-del-proyecto)
2. [Estructura de carpetas](#2-estructura-de-carpetas)
3. [Frontend (React + Vite)](#3-frontend-react--vite)
4. [Backend (Python + FastAPI)](#4-backend-python--fastapi)
5. [Blockchain privada en AWS (Hyperledger Fabric)](#5-blockchain-privada-en-aws-hyperledger-fabric)
6. [Chaincode (Smart Contract en Go)](#6-chaincode-smart-contract-en-go)
7. [Guia paso a paso: como se configuro la blockchain en AWS](#7-guia-paso-a-paso-como-se-configuro-la-blockchain-en-aws)
8. [Flujo completo: que pasa cuando se crea un paciente](#8-flujo-completo-que-pasa-cuando-se-crea-un-paciente)
9. [Proximo paso: conectar el backend con la blockchain](#9-proximo-paso-conectar-el-backend-con-la-blockchain)
10. [Glosario de terminos](#10-glosario-de-terminos)
11. [Como apagar todo en AWS para no pagar](#11-como-apagar-todo-en-aws-para-no-pagar)
12. [Como levantar todo de nuevo en AWS](#12-como-levantar-todo-de-nuevo-en-aws)

---

## 1. Vision general del proyecto

Este proyecto es una aplicacion web para gestionar el **empadronamiento de pacientes** en un sistema de salud. La particularidad es que cada alta de paciente se registra tambien en una **blockchain privada** alojada en AWS, lo que garantiza que el registro es **inmutable** (nadie puede modificarlo despues) y **auditable** (se puede consultar el historial completo de cambios).

### Diagrama simplificado

```
+-------------------+        +-------------------+        +-------------------------+
|                   |  HTTP  |                   |  gRPC  |                         |
|   Frontend        +------->+   Backend         +------->+   Blockchain (AWS)      |
|   (React + Vite)  |        |   (FastAPI)       |        |   Hyperledger Fabric    |
|   Puerto 5500     |        |   Puerto 9999     |        |   Chaincode en Go       |
|                   |        |                   |        |                         |
+-------------------+        +-------------------+        +-------------------------+
     Navegador               Servidor Python               Red privada en la nube
```

**En palabras simples:**
- El **frontend** es lo que el usuario ve en el navegador (formularios, tablas, botones).
- El **backend** es el servidor que recibe los datos del frontend, los procesa y los guarda.
- La **blockchain** es una base de datos distribuida e inmutable donde se registra cada operacion critica (como crear un paciente).

---

## 2. Estructura de carpetas

```
I2961-SwissEmpadronamiento/
|
|-- backend/                    <-- Servidor API en Python
|   |-- main.py                 <-- Punto de entrada del servidor
|   |-- dependencies.py         <-- Inyeccion de dependencias
|   |-- datosSinteticos.py      <-- Script para generar datos de prueba
|   |-- models/                 <-- Definicion de datos (como luce un paciente, etc.)
|   |   |-- patient.py
|   |   |-- enrollment.py
|   |   |-- agreement.py
|   |   |-- medication.py
|   |   |-- monodrug.py
|   |   |-- bulk_import.py
|   |-- repositories/           <-- Donde se almacenan los datos (en memoria)
|   |   |-- patient_repo.py
|   |   |-- enrollment_repo.py
|   |   |-- agreement_repo.py
|   |   |-- medication_repo.py
|   |   |-- monodrug_repo.py
|   |-- routers/                <-- Endpoints de la API (las URLs que acepta)
|   |   |-- patient_router.py
|   |   |-- enrollment_router.py
|   |   |-- agreement_router.py
|   |   |-- medication_router.py
|   |   |-- monodrug_router.py
|   |-- services/               <-- Logica de negocio
|       |-- patient_service.py
|       |-- enrollment_service.py
|       |-- agreement_service.py
|       |-- medication_service.py
|       |-- monodrug_service.py
|       |-- excel_import_service.py
|
|-- frontend/                   <-- Aplicacion web en React
|   |-- index.html
|   |-- vite.config.js          <-- Configuracion del servidor de desarrollo
|   |-- package.json            <-- Dependencias de Node.js
|   |-- src/
|   |   |-- App.jsx             <-- Componente principal
|   |   |-- main.jsx            <-- Punto de entrada de React
|   |   |-- index.css           <-- Estilos globales
|   |   |-- api/                <-- Funciones para llamar al backend
|   |   |-- components/         <-- Componentes reutilizables (tablas, formularios, etc.)
|   |   |-- hooks/              <-- Hooks personalizados de React
|   |   |-- pages/              <-- Paginas de la aplicacion
|
|-- ml-models/                  <-- Modulo de inteligencia artificial
|   |-- datosSinteticos.py      <-- Generacion de datasets sinteticos de diabetes
|
|-- blockchain/                 <-- Smart Contract en Go (desplegado en AWS)
|   |-- main.go                 <-- Codigo del contrato inteligente
|   |-- go.mod                  <-- Dependencias de Go
|
|-- requirements.txt            <-- Dependencias de Python
|-- .gitignore                  <-- Archivos ignorados por Git
|-- README.md                   <-- Documentacion basica
```

---

## 3. Frontend (React + Vite)

### Que es

El frontend es la **interfaz grafica** que el usuario ve en su navegador. Esta construido con:

| Tecnologia | Para que sirve |
|-----------|---------------|
| **React** | Libreria de JavaScript para construir interfaces de usuario con componentes |
| **Vite** | Herramienta que levanta un servidor de desarrollo rapido y construye la app para produccion |
| **JSX** | Sintaxis que permite escribir HTML dentro de JavaScript |

### Como funciona

1. El usuario abre `http://localhost:5500` en su navegador.
2. Vite sirve la aplicacion React.
3. Cuando el usuario completa un formulario (ej: crear paciente), React envia los datos al backend.
4. Vite actua como **proxy**: redirige las peticiones `/patients`, `/enrollments`, etc. al backend en `http://127.0.0.1:9999`.

### Configuracion del proxy (vite.config.js)

```javascript
server: {
    port: 5500,
    proxy: {
      "/patients": "http://127.0.0.1:9999",
      "/agreements": "http://127.0.0.1:9999",
      "/enrollments": "http://127.0.0.1:9999",
      "/medications": "http://127.0.0.1:9999",
      "/monodrugs": "http://127.0.0.1:9999",
    },
}
```

**Por que un proxy?** Porque el frontend corre en el puerto 5500 y el backend en el 9999. Sin proxy, el navegador bloquearia las peticiones por politicas de seguridad (CORS). El proxy hace que todo parezca venir del mismo servidor.

### Paginas principales

| Pagina | Que hace |
|--------|---------|
| `PacientesPage` | Formulario para dar de alta un paciente |
| `EmpadronamientoPage` | Formulario para crear un empadronamiento |
| `AcuerdoPage` | Gestion de acuerdos |
| `AltaMedicamentosPage` | Alta de medicamentos |
| `MonodrogasPage` | Gestion de monodrogas |
| `HistorialPacientesPage` | Tabla con el historial de pacientes |
| `HistorialEmpadronamientosPage` | Tabla con el historial de empadronamientos |
| `HistorialMedicamentosPage` | Tabla con el historial de medicamentos |
| `HistorialMonodrogasPage` | Tabla con el historial de monodrogas |

### Como levantar el frontend

```bash
cd frontend
npm install        # Instala dependencias (solo la primera vez)
npm run dev        # Levanta el servidor de desarrollo en http://localhost:5500
```

---

## 4. Backend (Python + FastAPI)

### Que es

El backend es el **servidor** que recibe peticiones del frontend, procesa la logica de negocio y devuelve respuestas. Esta construido con:

| Tecnologia | Para que sirve |
|-----------|---------------|
| **Python 3.11** | Lenguaje de programacion |
| **FastAPI** | Framework web moderno y rapido para crear APIs |
| **Uvicorn** | Servidor ASGI que ejecuta la aplicacion FastAPI |
| **Pydantic** | Libreria para validar datos automaticamente |
| **Pandas / Openpyxl** | Para importar pacientes desde archivos Excel |

### Arquitectura del backend (capas)

El backend sigue un patron de **capas separadas**:

```
Peticion HTTP
     |
     v
+-----------+     +-----------+     +--------------+
|  Router   |---->|  Service  |---->|  Repository  |
| (URL)     |     | (Logica)  |     | (Datos)      |
+-----------+     +-----------+     +--------------+
```

| Capa | Archivo ejemplo | Que hace |
|------|----------------|---------|
| **Router** | `patient_router.py` | Define las URLs (endpoints) que acepta la API. Recibe los datos del frontend. |
| **Service** | `patient_service.py` | Contiene la logica de negocio. Valida datos, crea objetos, coordina operaciones. |
| **Repository** | `patient_repo.py` | Almacena y recupera los datos. Actualmente usa almacenamiento **en memoria** (los datos se pierden al reiniciar). |
| **Model** | `patient.py` | Define la **forma** de los datos: que campos tiene un paciente, de que tipo son, cuales son obligatorios. |

### Ejemplo: como se crea un paciente

1. El frontend envia un `POST /patients` con los datos del formulario.
2. `patient_router.py` recibe la peticion y extrae los campos del formulario.
3. Llama a `patient_service.py` -> metodo `create()`.
4. El servicio crea un objeto `Patient` con un ID autoincrementable.
5. Lo guarda en `patient_repo.py` (una lista en memoria).
6. Devuelve el paciente creado al frontend como JSON.

### Modelo de paciente (simplificado)

```python
class Patient(BaseModel):
    id: int
    sap_id: str                     # ID del paciente en SAP
    first_name: str                 # Nombre
    last_name: str                  # Apellido
    birth_date: date                # Fecha de nacimiento
    gender: str                     # Genero
    tipo_empadronamiento: str       # Tipo de empadronamiento
    fecha_inicio: date              # Fecha de inicio
    blockchain_tx_id: Optional[str] # ID de la transaccion en blockchain (futuro)
    # ... otros campos opcionales
```

El campo `blockchain_tx_id` fue agregado para guardar el identificador de la transaccion en blockchain cuando se registre el paciente ahi. Actualmente es `None` porque la conexion backend-blockchain aun no esta implementada.

### Como levantar el backend

```bash
# Crear entorno virtual (solo la primera vez)
python -m venv .venv

# Activar entorno virtual
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Levantar el servidor
python -m backend.main
# El servidor corre en http://127.0.0.1:9999
```

---

## 5. Blockchain privada en AWS (Hyperledger Fabric)

### Que es una blockchain

Una **blockchain** es una base de datos distribuida donde los registros:
- **Son inmutables**: una vez guardado, un dato no se puede modificar ni borrar.
- **Son auditables**: se puede ver el historial completo de cambios de cada registro.
- **Son verificables**: cada transaccion tiene una firma criptografica.

### Blockchain publica vs privada

| Caracteristica | Publica (ej: Ethereum) | Privada (ej: Hyperledger Fabric) |
|---------------|----------------------|--------------------------------|
| Quien puede participar | Cualquiera | Solo miembros autorizados |
| Transparencia | Todo es publico | Solo los miembros ven los datos |
| Velocidad | Lenta (miles de nodos) | Rapida (pocos nodos controlados) |
| Costo | Hay que pagar "gas" por transaccion | Sin costos de gas |
| Uso tipico | Criptomonedas, NFTs | Salud, supply chain, auditoria |

Para este proyecto usamos **Hyperledger Fabric** porque es una blockchain **privada/permisionada**: solo nuestros servidores autorizados pueden leer y escribir datos. Esto es fundamental en salud donde los datos de pacientes son sensibles.

### AWS Managed Blockchain

En vez de instalar Hyperledger Fabric manualmente en servidores, usamos **AWS Managed Blockchain**, que es un servicio de Amazon que:
- Crea y administra la red de blockchain automaticamente.
- Maneja los certificados de seguridad.
- Escala automaticamente.
- Elimina la necesidad de ser un experto en infraestructura de blockchain.

### Componentes de la red

```
+----------------------------------------------------------+
|                    Red de Blockchain                       |
|                 (Network en AWS)                          |
|                                                          |
|  +--------------------+     +------------------------+   |
|  |   Miembro          |     |   Orderer Service      |   |
|  |   (Member)         |     |   (Servicio de orden)  |   |
|  |                    |     |                        |   |
|  |  +-------------+  |     |  Recibe transacciones   |   |
|  |  | Peer Node   |  |     |  y las ordena en        |   |
|  |  | (Nodo par)  |  |     |  bloques                |   |
|  |  +-------------+  |     +------------------------+   |
|  |                    |                                  |
|  |  +-------------+  |                                  |
|  |  | Fabric CA   |  |                                  |
|  |  | (Autoridad  |  |                                  |
|  |  | certificados)|  |                                  |
|  |  +-------------+  |                                  |
|  +--------------------+                                  |
+----------------------------------------------------------+
```

| Componente | Que es | Analogia simple |
|-----------|--------|----------------|
| **Network** | La red completa de blockchain | La "empresa" completa |
| **Member** | Tu organizacion dentro de la red | Tu "departamento" dentro de la empresa |
| **Peer Node** | Un servidor que guarda una copia del libro de registros | Un "empleado" que guarda una copia del libro contable |
| **Orderer** | El servicio que recibe transacciones y las ordena en bloques | El "contador jefe" que ordena las facturas cronologicamente |
| **Fabric CA** | Autoridad de certificados: emite "carnets de identidad" digitales | La oficina de RRHH que emite credenciales |
| **Channel** | Un canal privado donde se ejecutan transacciones | Una "sala de reuniones privada" donde solo ciertos miembros pueden operar |
| **Chaincode** | El programa (smart contract) que define las reglas de negocio | Las "reglas del juego" escritas en codigo |

---

## 6. Chaincode (Smart Contract en Go)

### Que es un chaincode

Un **chaincode** (tambien llamado "smart contract") es un programa que vive dentro de la blockchain y define:
- **Que datos se pueden guardar** (ej: pacientes con nombre, apellido, fecha de nacimiento).
- **Que operaciones se pueden hacer** (ej: crear paciente, consultar paciente, ver historial).
- **Que reglas de validacion existen** (ej: no se puede crear un paciente duplicado).

### Por que Go y no Node.js

Inicialmente intentamos escribir el chaincode en **Node.js**, pero descubrimos que el runtime de Hyperledger Fabric 2.2 en AWS usa **Node.js 12**, mientras que las dependencias modernas del SDK de Fabric requieren **Node.js 15+**. Esto generaba errores de sintaxis irreconciliables.

La solucion fue reescribir el chaincode en **Go**, que:
- Tiene soporte nativo y estable en Fabric.
- No tiene problemas de version de runtime.
- Compila a un binario, asi que no depende de versiones de lenguaje en el servidor.

### Estructura del chaincode (main.go)

El archivo `blockchain/main.go` define tres funciones principales:

#### CreatePatient - Crear un paciente

```go
func (pc *PatientContract) CreatePatient(ctx contractapi.TransactionContextInterface,
    patientID string, dataJSON string) (string, error)
```

1. Recibe un `patientID` y un JSON con los datos del paciente.
2. Verifica que no exista un paciente con ese ID (evita duplicados).
3. Parsea el JSON y agrega metadatos (tipo de documento, timestamp).
4. Guarda el paciente en el ledger (libro de registros de la blockchain).
5. Devuelve el paciente creado como JSON.

#### QueryPatient - Consultar un paciente

```go
func (pc *PatientContract) QueryPatient(ctx contractapi.TransactionContextInterface,
    patientID string) (string, error)
```

1. Recibe un `patientID`.
2. Busca el paciente en el ledger.
3. Devuelve los datos como JSON, o un error si no existe.

#### GetPatientHistory - Ver el historial de un paciente

```go
func (pc *PatientContract) GetPatientHistory(ctx contractapi.TransactionContextInterface,
    patientID string) (string, error)
```

1. Recibe un `patientID`.
2. Consulta **todas las versiones** del registro (cada vez que se modifico).
3. Devuelve un array con cada version, incluyendo:
   - `txId`: el ID unico de la transaccion.
   - `timestamp`: cuando se hizo el cambio.
   - `isDelete`: si fue una eliminacion.
   - `value`: el valor en ese momento.

### Datos que se guardan en la blockchain

```go
type Patient struct {
    DocType              string  // Siempre "patient" (para identificar el tipo)
    PatientID            string  // ID unico del paciente
    SapID                string  // ID del paciente en SAP
    FirstName            string  // Nombre
    LastName             string  // Apellido
    BirthDate            string  // Fecha de nacimiento
    Gender               string  // Genero
    TipoEmpadronamiento string  // Tipo de empadronamiento
    FechaInicio          string  // Fecha de inicio
    DataHash             string  // Hash de los datos (para verificacion)
    CreatedAt            string  // Fecha de creacion en la blockchain
}
```

---

## 7. Guia paso a paso: como se configuro la blockchain en AWS

A continuacion se detalla **todo lo que se hizo** para configurar la blockchain. Si necesitas recrear el entorno desde cero, segui estos pasos en orden.

### Paso 1: Crear la red de blockchain en AWS

1. Ir a la **consola de AWS** > buscar **"Managed Blockchain"**.
2. Click en **"Create network"**.
3. Configurar:
   - **Blockchain framework**: Hyperledger Fabric
   - **Framework version**: 2.2
   - **Network name**: un nombre descriptivo (ej: `swiss-empadronamiento-network`)
   - **Member name**: nombre de tu organizacion (ej: `SwissMedical`)
   - **Admin username**: `admin`
   - **Admin password**: una contrasena segura (anotarla, se usa despues)
4. Confirmar y esperar. La creacion toma **20-30 minutos**.

### Paso 2: Crear un Peer Node

Una vez que la red este en estado **"Available"**:

1. Ir a **Managed Blockchain** > tu red > **Members** > tu miembro.
2. Click en **"Create peer node"**.
3. Configurar:
   - **Instance type**: `bc.t3.small` (suficiente para desarrollo)
   - **Availability zone**: cualquiera
4. Esperar a que el peer este en estado **"Available"** (10-15 minutos).

### Paso 3: Crear un VPC Endpoint

El VPC Endpoint permite que una instancia EC2 se comunique con la blockchain de forma **privada** (sin pasar por internet publico).

1. Ir a **VPC** > **Endpoints** > **Create endpoint**.
2. Buscar el servicio de Managed Blockchain (filtrando por `managedblockchain`).
3. Seleccionar la **VPC** donde esta tu EC2.
4. Seleccionar las **subredes**.
5. Habilitar **"Private DNS names"**.
6. Crear el endpoint.

**Configuracion critica de la VPC:**
- En la VPC, habilitar **"DNS hostnames"** = `Enabled`.
- En la VPC, habilitar **"DNS resolution"** = `Enabled`.

### Paso 4: Configurar Security Groups

Los Security Groups son "firewalls virtuales" que controlan que trafico puede entrar y salir.

**Security Group de la EC2** (donde corre el Fabric CLI):
| Tipo | Puerto | Origen |
|------|--------|--------|
| SSH | 22 | Tu IP |
| All traffic | Todo | CIDR de la VPC (ej: `172.31.0.0/16`) |

**Security Group del VPC Endpoint** (el grupo `default` de la VPC):
| Tipo | Puerto | Origen |
|------|--------|--------|
| All traffic | Todo | CIDR de la VPC (ej: `172.31.0.0/16`) |

> **Leccion aprendida:** Si el Fabric CLI no puede conectarse al CA, Peer u Orderer, lo primero que hay que revisar son los Security Groups. El error tipico es `connection timed out`.

### Paso 5: Lanzar una instancia EC2

Esta EC2 actua como "maquina cliente" para interactuar con la blockchain.

1. Ir a **EC2** > **Launch instance**.
2. Configurar:
   - **AMI**: Amazon Linux 2023
   - **Instance type**: `t2.micro` o `t2.small`
   - **VPC**: la misma VPC que el VPC Endpoint
   - **Security group**: el configurado en el paso anterior
   - **Key pair**: crear o seleccionar uno para SSH
3. Lanzar la instancia.

### Paso 6: Instalar herramientas en la EC2

Conectarse a la EC2 por SSH o EC2 Instance Connect, y ejecutar:

```bash
# Actualizar paquetes
sudo yum update -y

# Instalar Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Cerrar sesion y volver a conectar para que el grupo docker aplique
exit
# (reconectar)

# Verificar Docker
docker --version

# Instalar Go (necesario para compilar el chaincode)
sudo yum install -y golang

# Verificar Go
go version
```

### Paso 7: Descargar certificados TLS de AWS

```bash
# Crear directorio para certificados
mkdir -p /home/ec2-user/managedblockchain-tls-chain

# Descargar el certificado TLS de AWS Managed Blockchain
aws s3 cp s3://us-east-1.managedblockchain/etc/managedblockchain-tls-chain.pem \
    /home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem

# Si no funciona con S3, descargar directamente:
wget https://s3.us-east-1.amazonaws.com/us-east-1.managedblockchain/etc/managedblockchain-tls-chain.pem \
    -O /home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem
```

### Paso 8: Enrollar el admin con Fabric CA

El **enrollment** es el proceso de obtener credenciales (certificados) de la autoridad certificadora (CA).

```bash
# Descargar el binario de fabric-ca-client
# (version compatible con Fabric 2.2)
wget https://github.com/hyperledger/fabric-ca/releases/download/v1.5.5/hyperledger-fabric-ca-linux-amd64-1.5.5.tar.gz
tar xzf hyperledger-fabric-ca-linux-amd64-1.5.5.tar.gz
sudo mv bin/fabric-ca-client /usr/local/bin/

# Obtener el endpoint del CA desde la consola de AWS:
# Managed Blockchain > tu red > Members > tu miembro > "Certificate authority endpoint"
# Se ve algo como: ca.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30002

# Enrollar el admin
export CA_ENDPOINT=ca.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30002

fabric-ca-client enroll \
    -u 'https://admin:TU_PASSWORD@'$CA_ENDPOINT \
    --tls.certfiles /home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem \
    -M /home/ec2-user/admin-msp
```

> **Leccion aprendida:** Usar comillas simples alrededor de la URL para evitar que bash interprete caracteres especiales en la contrasena. Si la contrasena tiene `!`, `$` u otros caracteres especiales, las comillas simples son obligatorias.

> **Leccion aprendida:** Si da error de autenticacion (`Error Code: 20`), primero borrar `rm -rf /home/ec2-user/admin-msp` y reintentar. Verificar que el username es `admin` (no `AdminUser` ni otro).

### Paso 9: Crear el canal (Channel)

#### 9a. Crear archivo configtx.yaml

```bash
mkdir -p /home/ec2-user/config
cat > /home/ec2-user/configtx.yaml << 'EOF'
Organizations:
    - &Org1
        Name: m-XXXXXX  # <-- Reemplazar con tu Member ID
        ID: m-XXXXXX
        MSPDir: /home/ec2-user/admin-msp
        Policies:
            Readers:
                Type: Signature
                Rule: "OR('m-XXXXXX.member')"
            Writers:
                Type: Signature
                Rule: "OR('m-XXXXXX.member')"
            Admins:
                Type: Signature
                Rule: "OR('m-XXXXXX.admin')"
            Endorsement:
                Type: Signature
                Rule: "OR('m-XXXXXX.member')"

Application:
    Policies:
        Readers:
            Type: ImplicitMeta
            Rule: "ANY Readers"
        Writers:
            Type: ImplicitMeta
            Rule: "ANY Writers"
        Admins:
            Type: ImplicitMeta
            Rule: "ANY Admins"
        LifecycleEndorsement:
            Type: ImplicitMeta
            Rule: "ANY Endorsement"
        Endorsement:
            Type: ImplicitMeta
            Rule: "ANY Endorsement"
    Organizations:
        - *Org1

Channel:
    Policies:
        Readers:
            Type: ImplicitMeta
            Rule: "ANY Readers"
        Writers:
            Type: ImplicitMeta
            Rule: "ANY Writers"
        Admins:
            Type: ImplicitMeta
            Rule: "ANY Admins"

Profiles:
    OneOrgChannel:
        Consortium: AWSSystemConsortium
        <<: *ChannelDefaults
        Application:
            <<: *ApplicationDefaults
            Organizations:
                - *Org1

ChannelDefaults: &ChannelDefaults
    Policies:
        Readers:
            Type: ImplicitMeta
            Rule: "ANY Readers"
        Writers:
            Type: ImplicitMeta
            Rule: "ANY Writers"
        Admins:
            Type: ImplicitMeta
            Rule: "ANY Admins"

ApplicationDefaults: &ApplicationDefaults
    Policies:
        Readers:
            Type: ImplicitMeta
            Rule: "ANY Readers"
        Writers:
            Type: ImplicitMeta
            Rule: "ANY Writers"
        Admins:
            Type: ImplicitMeta
            Rule: "ANY Admins"
        LifecycleEndorsement:
            Type: ImplicitMeta
            Rule: "ANY Endorsement"
        Endorsement:
            Type: ImplicitMeta
            Rule: "ANY Endorsement"
    Organizations:
EOF
```

> **Nota importante:** El consorcio debe ser `AWSSystemConsortium` (no un nombre personalizado). AWS Managed Blockchain usa este nombre internamente.

#### 9b. Descargar herramientas de Fabric CLI

```bash
# Descargar los binarios de Fabric 2.2
wget https://github.com/hyperledger/fabric/releases/download/v2.2.12/hyperledger-fabric-linux-amd64-2.2.12.tar.gz
tar xzf hyperledger-fabric-linux-amd64-2.2.12.tar.gz
sudo mv bin/* /usr/local/bin/

# Descargar core.yaml (archivo de configuracion del peer)
mkdir -p /home/ec2-user/config
# Copiar core.yaml desde los binarios descargados o desde el repositorio de Fabric
cp config/core.yaml /home/ec2-user/config/
```

#### 9c. Generar el bloque genesis del canal

```bash
export FABRIC_CFG_PATH=/home/ec2-user/

configtxgen \
    -profile OneOrgChannel \
    -outputCreateChannelTx /home/ec2-user/patient-channel.pb \
    -channelID patient-channel
```

#### 9d. Crear el canal

```bash
# Obtener los endpoints desde la consola de AWS:
# - Orderer endpoint: orderer.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30001
# - Peer endpoint: nd-ZZZZZZ.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30003

export ORDERER_ENDPOINT=orderer.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30001
export PEER_ENDPOINT=nd-ZZZZZZ.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30003
export MSP_ID=m-XXXXXX
export TLS_CERT=/home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem
export FABRIC_CFG_PATH=/home/ec2-user/config/

docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    hyperledger/fabric-tools:2.2 \
    peer channel create \
        -c patient-channel \
        -f /home/ec2-user/patient-channel.pb \
        -o $ORDERER_ENDPOINT \
        --tls --cafile $TLS_CERT
```

#### 9e. Unir el peer al canal

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    hyperledger/fabric-tools:2.2 \
    peer channel join -b /home/ec2-user/patient-channel.block
```

> **Leccion aprendida:** Si obtienes un error de `x509: certificate is valid for X, not Y` o `context deadline exceeded`, **verificar muy bien el endpoint del peer node**. Un solo caracter mal en el ID del nodo causa este error. Copiar el endpoint directamente desde la consola de AWS.

### Paso 10: Desplegar el chaincode (Smart Contract)

#### 10a. Subir el codigo del chaincode a la EC2

```bash
# Crear directorio
mkdir -p /home/ec2-user/chaincode-go

# Copiar los archivos main.go y go.mod (via SCP, nano, o git clone)
```

#### 10b. Compilar las dependencias del chaincode

```bash
cd /home/ec2-user/chaincode-go
go mod tidy
go mod vendor
```

#### 10c. Empaquetar el chaincode

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode package /home/ec2-user/patient-cc.tar.gz \
        --path /home/ec2-user/chaincode-go \
        --lang golang \
        --label patient-cc_2.0
```

#### 10d. Instalar el chaincode en el peer

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode install /home/ec2-user/patient-cc.tar.gz
```

Esto devuelve un **Package ID** que necesitas para los siguientes pasos. Se ve algo como:
```
patient-cc_2.0:abc123def456...
```

#### 10e. Aprobar el chaincode

```bash
export CC_PACKAGE_ID=patient-cc_2.0:abc123def456...  # <-- Usar el ID real

docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode approveformyorg \
        --channelID patient-channel \
        --name patient-cc \
        --version 2.0 \
        --package-id $CC_PACKAGE_ID \
        --sequence 2 \
        --tls --cafile $TLS_CERT \
        -o $ORDERER_ENDPOINT
```

#### 10f. Hacer commit del chaincode

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode commit \
        --channelID patient-channel \
        --name patient-cc \
        --version 2.0 \
        --sequence 2 \
        --tls --cafile $TLS_CERT \
        -o $ORDERER_ENDPOINT
```

### Paso 11: Probar el chaincode

#### Crear un paciente de prueba

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer chaincode invoke \
        -C patient-channel \
        -n patient-cc \
        -c '{"function":"CreatePatient","Args":["PAT-001","{\"sapId\":\"SAP-001\",\"firstName\":\"Juan\",\"lastName\":\"Perez\",\"birthDate\":\"1990-01-15\",\"gender\":\"M\",\"tipoEmpadronamiento\":\"biologico\",\"fechaInicio\":\"2025-01-01\"}"]}' \
        --tls --cafile $TLS_CERT \
        -o $ORDERER_ENDPOINT
```

#### Consultar el paciente creado

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer chaincode query \
        -C patient-channel \
        -n patient-cc \
        -c '{"function":"QueryPatient","Args":["PAT-001"]}' \
        --tls --cafile $TLS_CERT
```

---

## 8. Flujo completo: que pasa cuando se crea un paciente

Una vez que el backend este conectado a la blockchain, el flujo sera:

```
1. Usuario llena formulario en el frontend
                  |
                  v
2. Frontend envia POST /patients al backend
                  |
                  v
3. Backend (patient_service.py) recibe los datos
                  |
                  v
4. Backend guarda el paciente en memoria (patient_repo.py)
                  |
                  v
5. Backend llama al BlockchainService (pendiente de implementar)
                  |
                  v
6. BlockchainService envia una transaccion "CreatePatient" a la blockchain
   con los datos del paciente en formato JSON
                  |
                  v
7. La blockchain (chaincode en Go) recibe la transaccion:
   a. Verifica que el paciente no exista
   b. Guarda el paciente en el ledger (libro inmutable)
   c. Devuelve un Transaction ID (txId)
                  |
                  v
8. Backend guarda el txId en el campo "blockchain_tx_id" del paciente
                  |
                  v
9. Backend devuelve el paciente completo al frontend
   (incluyendo el blockchain_tx_id para referencia)
                  |
                  v
10. Frontend muestra el resultado al usuario
```

### Por que este flujo es importante

- **Paso 4** (guardar en memoria): permite que la app funcione rapido, sin esperar a la blockchain.
- **Paso 6-7** (registrar en blockchain): crea un registro **inmutable** que nadie puede alterar despues.
- **Paso 8** (guardar txId): vincula el registro local con el registro en blockchain, permitiendo auditoria cruzada.

---

## 9. Proximo paso: conectar el backend con la blockchain

El siguiente paso es crear un `BlockchainService` en Python que se comunique con la blockchain. Esto implica:

1. **Instalar el SDK de Fabric para Python** o usar la **API Gateway de AWS** como intermediario.
2. **Crear `backend/services/blockchain_service.py`** con metodos como:
   - `register_patient(patient_data)` -> devuelve `txId`
   - `query_patient(patient_id)` -> devuelve datos desde blockchain
   - `get_patient_history(patient_id)` -> devuelve historial
3. **Modificar `patient_service.py`** para que despues de guardar en el repo, llame al `BlockchainService`.
4. **Guardar el `txId`** en el campo `blockchain_tx_id` del paciente.

### Opciones de conexion

| Opcion | Complejidad | Descripcion |
|--------|------------|-------------|
| **SDK de Fabric (Python/Node.js)** | Alta | Conexion directa al peer. Requiere certificados y configuracion TLS. |
| **API Gateway + Lambda** | Media | AWS Lambda ejecuta los comandos del peer y expone una API REST. |
| **Proxy en la EC2** | Baja | Un servicio REST en la EC2 que recibe peticiones del backend y ejecuta los comandos `peer`. |

---

## 10. Glosario de terminos

| Termino | Definicion |
|---------|-----------|
| **API** | Interfaz de programacion: un conjunto de URLs que un servidor expone para recibir y enviar datos. |
| **Backend** | El servidor que procesa la logica. No tiene interfaz visual; solo recibe y envia datos. |
| **Blockchain** | Base de datos distribuida donde los registros son inmutables y auditables. |
| **CA (Certificate Authority)** | Autoridad certificadora: emite credenciales digitales para identificar a los participantes de la red. |
| **Chaincode** | Programa (smart contract) que define las reglas de negocio dentro de la blockchain. |
| **Channel** | Canal privado dentro de la red donde se ejecutan transacciones. Solo los miembros del canal pueden ver los datos. |
| **CORS** | Cross-Origin Resource Sharing: politica de seguridad del navegador que restringe peticiones entre distintos origenes. |
| **Docker** | Herramienta que empaqueta aplicaciones en "contenedores" aislados, asegurando que funcionen igual en cualquier maquina. |
| **EC2** | Elastic Compute Cloud: servicio de AWS que proporciona servidores virtuales en la nube. |
| **Endpoint** | La direccion (URL + puerto) donde un servicio esta disponible para recibir peticiones. |
| **Enrollment** | Proceso de registrar una identidad con la CA para obtener certificados. |
| **FastAPI** | Framework de Python para crear APIs web rapidas y con documentacion automatica. |
| **Frontend** | La parte visual de la aplicacion: lo que el usuario ve en el navegador. |
| **Go (Golang)** | Lenguaje de programacion creado por Google, usado para el chaincode por su estabilidad con Fabric. |
| **gRPC** | Protocolo de comunicacion usado internamente por Hyperledger Fabric para las transacciones. |
| **Hyperledger Fabric** | Framework de blockchain privada/permisionada, mantenido por la Linux Foundation. |
| **Ledger** | El "libro mayor" de la blockchain: contiene todos los registros y transacciones. |
| **Member** | Una organizacion participante dentro de la red de blockchain. |
| **MSP** | Membership Service Provider: conjunto de certificados que identifican a un miembro de la red. |
| **Orderer** | Servicio que recibe transacciones y las ordena en bloques dentro de la blockchain. |
| **Peer** | Nodo de la red que almacena una copia del ledger y ejecuta el chaincode. |
| **Proxy** | Intermediario que redirige peticiones de un lugar a otro (ej: Vite redirige del frontend al backend). |
| **React** | Libreria de JavaScript para construir interfaces de usuario con componentes reutilizables. |
| **SDK** | Software Development Kit: conjunto de herramientas para interactuar con un servicio desde codigo. |
| **Security Group** | Firewall virtual de AWS que controla que trafico puede entrar y salir de un recurso. |
| **TLS** | Transport Layer Security: protocolo de cifrado que asegura la comunicacion entre servicios. |
| **Transaction ID (txId)** | Identificador unico de una transaccion en la blockchain. Sirve para rastrear y auditar operaciones. |
| **Vite** | Herramienta de desarrollo frontend que sirve la app con recarga en caliente y builds optimizados. |
| **VPC** | Virtual Private Cloud: red privada virtual dentro de AWS donde viven tus recursos. |
| **VPC Endpoint** | Punto de conexion que permite comunicacion privada entre recursos dentro de la VPC y servicios de AWS. |

---

## Errores comunes y como solucionarlos

| Error | Causa probable | Solucion |
|-------|---------------|----------|
| `no such host` al conectar con el CA | DNS no resuelve el hostname | Habilitar "DNS hostnames" en la VPC |
| `connection timed out` | Security Group bloqueando trafico | Agregar regla de inbound "All traffic" desde el CIDR de la VPC |
| `Authentication failure (Error Code: 20)` | Username o password incorrectos | Borrar `admin-msp/` y reintentar con username `admin` y password entre comillas simples |
| `Unknown consortium name` | Nombre de consorcio incorrecto en configtx.yaml | Usar `AWSSystemConsortium` |
| `no policies defined` | Faltan politicas en configtx.yaml | Agregar bloque `Policies` con Readers, Writers, Admins, Endorsement |
| `x509: certificate is valid for X, not Y` | Endpoint del peer incorrecto (typo en el ID del nodo) | Copiar el endpoint exacto desde la consola de AWS |
| `could not find config file` | `FABRIC_CFG_PATH` no apunta a donde esta `core.yaml` | Exportar `FABRIC_CFG_PATH=/home/ec2-user/config/` |
| `SyntaxError: Unexpected token '='` (Node.js chaincode) | Runtime de Fabric usa Node.js 12, incompatible con sintaxis moderna | Usar chaincode en Go en vez de Node.js |
| `docker-compose: command not found` | Amazon Linux 2023 no tiene docker-compose v1 | Usar `docker run` directamente en vez de docker-compose |

---

## 11. Como apagar todo en AWS para no pagar

AWS Managed Blockchain **no tiene un boton de "pausar"**. Los recursos cobran por hora mientras existen. Para dejar de pagar, hay que eliminar los recursos y recrearlos cuando se necesiten.

### Que se elimino y cuanto costaba

| # | Recurso | Accion realizada | Costo que se ahorra |
|---|---------|-----------------|-------------------|
| 1 | **Peer Node** (bc.t3.small) | Eliminado | ~$33/mes ($0.046/hora) |
| 2 | **EC2 Instance** (t2.micro) | **Detenida** (Stop, no Terminate) | ~$8.5/mes en compute (el disco EBS cobra ~$0.10/GB/mes, centavos) |
| 3 | **VPC Endpoint** | Eliminado | ~$7.3/mes ($0.01/hora) |
| 4 | **Member + Network** | Eliminados (al borrar el unico miembro, la red se elimina sola) | ~$218/mes ($0.30/hora del orderer) |

### Costo residual despues de apagar todo

| Recurso | Costo estimado | Nota |
|---------|---------------|------|
| Disco EBS de la EC2 (detenida) | ~$0.80/mes (8 GB x $0.10) | Es el disco de la instancia. Conserva todo lo instalado (Docker, Go, certificados, chaincode). |
| VPC | $0 | La VPC en si no tiene costo. |

**Total residual: menos de $1/mes** (solo el almacenamiento del disco de la EC2 detenida).

### Verificacion extra: otros recursos que podrian cobrar

Ir a la consola de AWS y revisar que no quede nada activo:

1. **EC2 > Elastic IPs**: Si hay alguna IP elastica **no asociada** a una instancia corriendo, cobra ~$3.6/mes. Si existe una, liberarla: **Actions > Release Elastic IP address**.

2. **EC2 > Volumes**: Verificar que no haya volumenes EBS huerfanos (sin instancia asociada). Si hay alguno que no se use, eliminarlo.

3. **CloudWatch > Log Groups**: Puede haber logs de Managed Blockchain. No cobran significativamente, pero se pueden eliminar: **Actions > Delete log group**.

4. **EC2 > Snapshots**: Si se crearon snapshots del disco, eliminarloss. Cobran $0.05/GB/mes.

5. **AWS Cost Explorer**: Ir a **Billing and Cost Management > Cost Explorer** para verificar que no haya cargos inesperados en los dias siguientes.

---

## 12. Como levantar todo de nuevo en AWS

Cuando necesites volver a usar la blockchain, segui estos pasos en orden. La EC2 ya tiene todo instalado (Docker, Go, fabric-ca-client, binarios de Fabric, core.yaml), asi que no hay que reinstalar nada.

### Tiempo estimado total: ~45 minutos

```
Paso 1: Crear red + miembro ............. 20-30 min (espera de AWS)
Paso 2: Crear peer node ................. 10-15 min (espera de AWS)
Paso 3: Recrear VPC Endpoint ............ 2-3 min
Paso 4: Iniciar la EC2 .................. 1 min
Paso 5: Enrollar admin con Fabric CA .... 2 min
Paso 6: Crear canal y unir peer ......... 5 min
Paso 7: Desplegar chaincode ............. 5 min
Paso 8: Probar .......................... 2 min
```

---

### Paso 1: Crear la red y el miembro

1. Ir a **AWS Console** > **Managed Blockchain** > **Create network**
2. Configurar:
   - **Framework**: Hyperledger Fabric 2.2
   - **Network name**: el nombre que quieras (ej: `medchain-network`)
   - **Member name**: nombre de tu organizacion (ej: `MedChainOrg`)
   - **Admin username**: `admin`
   - **Admin password**: elegir una contrasena segura y **anotarla** (la vas a necesitar en el Paso 5)
3. Confirmar y esperar **20-30 minutos** hasta que el estado sea **"Available"**

> **Anotar el Member ID** (tiene formato `m-XXXXXX...`). Lo vas a necesitar en varios pasos.

---

### Paso 2: Crear el Peer Node

1. Ir a **Managed Blockchain** > tu red > **Members** > tu miembro
2. Click **Create peer node**
3. Configurar:
   - **Instance type**: `bc.t3.small`
   - **Availability zone**: cualquiera
4. Esperar **10-15 minutos** hasta estado **"Available"**

> **Anotar el Peer Node endpoint** (tiene formato `nd-ZZZZZZ.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30003`). Copiarlo **exacto** desde la consola.

---

### Paso 3: Recrear el VPC Endpoint

1. Ir a **VPC** > **Endpoints** > **Create endpoint**
2. En el buscador de servicios, filtrar por `managedblockchain`
3. Seleccionar el servicio de tu red (contiene el Network ID)
4. Seleccionar la **misma VPC** donde esta tu EC2
5. Seleccionar las subredes
6. **Habilitar "Private DNS names"** (Enable DNS name = checked)
7. Security group: usar el grupo `default` de la VPC
8. Crear el endpoint

**Verificar configuracion de la VPC:**
- VPC > tu VPC > **Actions > Edit VPC settings**
  - **DNS hostnames**: `Enabled`
  - **DNS resolution**: `Enabled`

**Verificar Security Group del VPC Endpoint (grupo `default`):**
- Debe tener una regla inbound que permita **All traffic** desde el CIDR de la VPC (ej: `172.31.0.0/16`)

---

### Paso 4: Iniciar la EC2

1. Ir a **EC2** > **Instances**
2. Seleccionar tu instancia (esta en estado **Stopped**)
3. **Instance state** > **Start instance**
4. Esperar ~1 minuto hasta estado **Running**
5. Conectarse por **EC2 Instance Connect** o SSH

**Verificar que todo sigue instalado:**

```bash
docker --version
go version
fabric-ca-client version
ls /home/ec2-user/config/core.yaml
ls /home/ec2-user/chaincode-go/main.go
```

Todo deberia estar ahi porque solo detuvimos la instancia, no la terminamos.

---

### Paso 5: Enrollar el admin con el nuevo Fabric CA

Cada vez que se crea una red nueva, el CA es nuevo y necesita un enrollment nuevo.

```bash
# Borrar credenciales anteriores (del CA anterior que ya no existe)
rm -rf /home/ec2-user/admin-msp

# Obtener el nuevo endpoint del CA desde la consola de AWS:
# Managed Blockchain > tu red > Members > tu miembro > "Certificate authority endpoint"
# Formato: ca.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30002

# Descargar certificado TLS (si no lo tenes ya)
ls /home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem
# Si no existe:
# wget https://s3.us-east-1.amazonaws.com/us-east-1.managedblockchain/etc/managedblockchain-tls-chain.pem \
#     -O /home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem

# Enrollar el admin (usar comillas simples para la URL)
# Reemplazar CA_ENDPOINT y TU_PASSWORD con los valores reales
fabric-ca-client enroll \
    -u 'https://admin:TU_PASSWORD@ca.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30002' \
    --tls.certfiles /home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem \
    -M /home/ec2-user/admin-msp
```

> **Si da error `no such host`**: esperar 2-3 minutos a que el DNS del VPC Endpoint se propague.
>
> **Si da error `connection timed out`**: revisar el Security Group del VPC Endpoint (paso 3).
>
> **Si da error `Authentication failure`**: verificar username (`admin`) y password. Borrar `admin-msp/` y reintentar.

---

### Paso 6: Crear el canal y unir el peer

**Definir variables de entorno** (reemplazar con los valores nuevos de la consola de AWS):

```bash
# Estos valores cambian con cada red nueva. Copiarlos de la consola de AWS.
export MSP_ID=m-XXXXXX                    # Tu Member ID
export ORDERER_ENDPOINT=orderer.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30001
export PEER_ENDPOINT=nd-ZZZZZZ.m-XXXXXX.n-YYYYYY.managedblockchain.us-east-1.amazonaws.com:30003
export TLS_CERT=/home/ec2-user/managedblockchain-tls-chain/managedblockchain-tls-chain.pem
export FABRIC_CFG_PATH=/home/ec2-user/config/
```

#### 6a. Actualizar configtx.yaml con el nuevo Member ID

```bash
# Editar configtx.yaml y reemplazar el Member ID anterior por el nuevo
# El Member ID aparece en los campos Name, ID, y en las Rules de Policies
nano /home/ec2-user/configtx.yaml

# En todas las lineas que digan m-VIEJO, cambiar por m-NUEVO
# Hay ~6 ocurrencias que cambiar
```

#### 6b. Generar el bloque genesis del canal

```bash
export FABRIC_CFG_PATH=/home/ec2-user/

configtxgen \
    -profile OneOrgChannel \
    -outputCreateChannelTx /home/ec2-user/patient-channel.pb \
    -channelID patient-channel
```

#### 6c. Crear el canal

```bash
export FABRIC_CFG_PATH=/home/ec2-user/config/

docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    hyperledger/fabric-tools:2.2 \
    peer channel create \
        -c patient-channel \
        -f /home/ec2-user/patient-channel.pb \
        -o $ORDERER_ENDPOINT \
        --tls --cafile $TLS_CERT
```

#### 6d. Unir el peer al canal

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    hyperledger/fabric-tools:2.2 \
    peer channel join -b /home/ec2-user/patient-channel.block
```

> **Si da error `x509: certificate is valid for X, not Y`**: verificar que el PEER_ENDPOINT sea exactamente el que muestra la consola de AWS. Un solo caracter diferente causa este error.

---

### Paso 7: Desplegar el chaincode

El codigo del chaincode ya esta en `/home/ec2-user/chaincode-go/` desde la vez anterior.

#### 7a. Empaquetar

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode package /home/ec2-user/patient-cc.tar.gz \
        --path /home/ec2-user/chaincode-go \
        --lang golang \
        --label patient-cc_1.0
```

#### 7b. Instalar

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode install /home/ec2-user/patient-cc.tar.gz
```

> **Anotar el Package ID** que devuelve (formato: `patient-cc_1.0:abc123def456...`). Se necesita en el siguiente paso.

#### 7c. Aprobar

```bash
# Reemplazar CC_PACKAGE_ID con el valor real del paso anterior
export CC_PACKAGE_ID=patient-cc_1.0:abc123def456...

docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode approveformyorg \
        --channelID patient-channel \
        --name patient-cc \
        --version 1.0 \
        --package-id $CC_PACKAGE_ID \
        --sequence 1 \
        --tls --cafile $TLS_CERT \
        -o $ORDERER_ENDPOINT
```

#### 7d. Commit

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer lifecycle chaincode commit \
        --channelID patient-channel \
        --name patient-cc \
        --version 1.0 \
        --sequence 1 \
        --tls --cafile $TLS_CERT \
        -o $ORDERER_ENDPOINT
```

> **Nota sobre version y sequence**: Como es una red nueva, usamos `--version 1.0` y `--sequence 1`. Si en el futuro actualizas el chaincode en la misma red, incrementa ambos valores (2.0/2, 3.0/3, etc.).

---

### Paso 8: Probar que todo funciona

#### Crear un paciente de prueba

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer chaincode invoke \
        -C patient-channel \
        -n patient-cc \
        -c '{"function":"CreatePatient","Args":["PAT-001","{\"sapId\":\"SAP-001\",\"firstName\":\"Juan\",\"lastName\":\"Perez\",\"birthDate\":\"1990-01-15\",\"gender\":\"M\",\"tipoEmpadronamiento\":\"biologico\",\"fechaInicio\":\"2025-01-01\"}"]}' \
        --tls --cafile $TLS_CERT \
        -o $ORDERER_ENDPOINT
```

#### Consultar el paciente

```bash
docker run --rm \
    -v /home/ec2-user:/home/ec2-user \
    -e FABRIC_CFG_PATH=/home/ec2-user/config/ \
    -e CORE_PEER_TLS_ENABLED=true \
    -e CORE_PEER_TLS_ROOTCERT_FILE=$TLS_CERT \
    -e CORE_PEER_LOCALMSPID=$MSP_ID \
    -e CORE_PEER_MSPCONFIGPATH=/home/ec2-user/admin-msp \
    -e CORE_PEER_ADDRESS=$PEER_ENDPOINT \
    hyperledger/fabric-tools:2.2 \
    peer chaincode query \
        -C patient-channel \
        -n patient-cc \
        -c '{"function":"QueryPatient","Args":["PAT-001"]}' \
        --tls --cafile $TLS_CERT
```

Si el query devuelve el JSON del paciente, **todo esta funcionando correctamente**.

---

### Checklist rapido para levantar todo

```
[ ] 1. Crear red + miembro en Managed Blockchain (anotar Member ID y password)
[ ] 2. Esperar 20-30 min a que este "Available"
[ ] 3. Crear Peer Node (anotar endpoint exacto)
[ ] 4. Esperar 10-15 min a que este "Available"
[ ] 5. Crear VPC Endpoint (habilitar Private DNS, DNS hostnames en VPC)
[ ] 6. Verificar Security Group del VPC Endpoint (All traffic desde CIDR de VPC)
[ ] 7. Iniciar EC2 (Start instance)
[ ] 8. Conectarse a la EC2
[ ] 9. Borrar admin-msp anterior: rm -rf /home/ec2-user/admin-msp
[ ] 10. Enrollar admin con el nuevo CA endpoint
[ ] 11. Actualizar configtx.yaml con el nuevo Member ID
[ ] 12. Generar bloque genesis (configtxgen)
[ ] 13. Crear canal (peer channel create)
[ ] 14. Unir peer al canal (peer channel join)
[ ] 15. Empaquetar chaincode (peer lifecycle chaincode package)
[ ] 16. Instalar chaincode (peer lifecycle chaincode install)
[ ] 17. Aprobar chaincode (peer lifecycle chaincode approveformyorg)
[ ] 18. Commit chaincode (peer lifecycle chaincode commit)
[ ] 19. Probar con invoke + query
```

---

### Como volver a apagar todo

Seguir el mismo orden que la primera vez:

```
1. Eliminar Peer Node        (Managed Blockchain > tu red > Members > Peer nodes > Delete)
2. Eliminar Member           (Managed Blockchain > tu red > Members > Delete member)
   -> La red se elimina sola si eras el unico miembro
3. Eliminar VPC Endpoint     (VPC > Endpoints > Actions > Delete)
4. Detener EC2               (EC2 > Instances > Instance state > Stop instance)
```
