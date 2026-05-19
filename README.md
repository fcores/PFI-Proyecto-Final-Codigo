# MedChain AI

Sistema de gestión de empadronamiento de pacientes con registro inmutable en blockchain privada (Hyperledger Fabric en AWS).

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| **Frontend** | React + Vite (puerto 5500) |
| **Backend** | Python 3.11 + FastAPI (puerto 9999) |
| **Modelo IA** | Python — generación de datos sintéticos para clasificación de diabetes |
| **Blockchain** | AWS Managed Blockchain — Hyperledger Fabric 2.2 |
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
├── blockchain/              Smart contract en Go (desplegado en AWS)
│   ├── main.go              CreatePatient, QueryPatient, GetPatientHistory
│   └── go.mod               Dependencias (fabric-contract-api-go)
├── requirements.txt         Dependencias de Python
└── ARQUITECTURA PASO A PASO.md   Documentación detallada de la arquitectura
```

## Instalación y ejecución

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

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/patients` | Crear paciente |
| `GET` | `/patients` | Listar pacientes |
| `POST` | `/patients/bulk-import` | Importar pacientes desde Excel |
| `POST` | `/enrollments` | Crear empadronamiento |
| `GET` | `/enrollments` | Listar empadronamientos |
| `POST` | `/medications` | Crear medicamento |
| `GET` | `/medications` | Listar medicamentos |
| `POST` | `/monodrugs` | Crear monodroga |
| `GET` | `/monodrugs` | Listar monodrogas |
| `POST` | `/agreements` | Crear acuerdo |
| `GET` | `/agreements` | Listar acuerdos |

## Blockchain

El chaincode en Go (`blockchain/main.go`) está desplegado en AWS Managed Blockchain y expone tres funciones:

- **CreatePatient** — Registra un paciente de forma inmutable en el ledger.
- **QueryPatient** — Consulta los datos actuales de un paciente.
- **GetPatientHistory** — Devuelve el historial completo de cambios de un paciente.

Para la guía paso a paso de configuración de la blockchain en AWS, ver [`ARQUITECTURA PASO A PASO.md`](ARQUITECTURA%20PASO%20A%20PASO.md).

## Notas

- Los datos del backend se almacenan **en memoria**; se pierden al reiniciar el servidor.
- El campo `blockchain_tx_id` en los modelos de paciente y empadronamiento está preparado para vincular cada registro con su transacción en blockchain (pendiente de integración).
- La carpeta `ml-models/` contiene los scripts de generación de datos sintéticos y será el módulo donde se implementen los modelos de IA del proyecto.
