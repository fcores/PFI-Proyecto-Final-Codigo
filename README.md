# Pantalla "Nuevo paciente" (FastAPI + HTML/CSS/JS)

Proyecto de ejemplo que replica la pantalla de "Nuevo paciente" usando:

- **Backend**: FastAPI
- **Frontend**: HTML + CSS + JavaScript puro

## Estructura

- `backend/main.py`: API FastAPI con endpoints para crear y listar pacientes (almacenados en memoria).
- `frontend/index.html`: Pantalla de "Nuevo paciente".
- `frontend/styles.css`: Estilos para Alleanza Tracking.
- `frontend/app.js`: Lógica para enviar el formulario y renderizar la tabla de pacientes.
- `requirements.txt`: Dependencias de Python.

## Instalación backend

```bash
cd d:\trabajo\I2961-SwissEmpadronamiento
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

La API quedará en `http://127.0.0.1:8000`.

## Ejecutar frontend

Opción rápida (abrir archivo):

- Abre `frontend/index.html` directamente en el navegador (doble clic).

Opción recomendada (servidor estático):

```bash
cd frontend
python -m http.server 5500
```

Luego abre `http://127.0.0.1:5500/index.html` en el navegador.

## Notas

- El "upload" de receta se maneja como archivo en el formulario; el backend solo guarda el **nombre del archivo** (no se persiste en disco).
- Los pacientes se almacenan en memoria; al reiniciar el servidor se limpia la lista.

