import logging
import os

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.ml.model_loader import cargar_modelo, modelo_disponible
from backend.routers import (
    patient_router,
    medication_router,
    monodrug_router,
    prescription_router,
    ledger_router,
    auth_router,
    audit_router,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Crea y configura la instancia FastAPI con routers bajo /api."""
    app = FastAPI(title="MedChain AI", version="0.6.0")

    raw_origins = os.getenv("CORS_ORIGINS")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api")
    api.include_router(patient_router)
    api.include_router(medication_router)
    api.include_router(monodrug_router)
    api.include_router(prescription_router)
    api.include_router(ledger_router)
    api.include_router(auth_router)
    api.include_router(audit_router)
    app.include_router(api)

    @app.get("/")
    async def root():
        """Health check (sin prefijo /api) que reporta el estado del modelo ML."""
        try:
            artefacto = cargar_modelo()
            version = artefacto.get("version_modelo") if artefacto else None
            return {
                "status": "ok",
                "service": "MedChain AI",
                "modelo_disponible": modelo_disponible(),
                "modelo_version": version,
            }
        except Exception as exc:
            logger.error("Error en health check root: %s", exc, exc_info=True)
            return {
                "status": "ok",
                "service": "MedChain AI",
                "modelo_disponible": False,
                "modelo_version": None,
            }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=9999, reload=True)
