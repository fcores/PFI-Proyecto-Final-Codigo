import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.db import init_db
from backend.error_handlers import install_error_handlers
from backend.ml.model_loader import cargar_modelo, modelo_disponible
from backend.routers import (
    audit_router,
    auth_router,
    ledger_router,
    medication_router,
    monodrug_router,
    patient_router,
    prescription_router,
)
from backend.security.phi_redactor import install_phi_filter

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Crea y configura la instancia FastAPI con routers bajo /api."""
    settings = get_settings()
    install_phi_filter()

    app = FastAPI(title="MedChain AI", version="0.7.0")
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()

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
        """Health check que reporta el estado del modelo ML y la base de datos."""
        from backend.db import is_db_available

        try:
            artefacto = cargar_modelo()
            version = artefacto.get("version_modelo") if artefacto else None
            return {
                "status": "ok",
                "service": "MedChain AI",
                "database": "connected" if is_db_available() else "in-memory",
                "modelo_disponible": modelo_disponible(),
                "modelo_version": version,
            }
        except Exception as exc:
            logger.error("Error en health check root: %s", exc, exc_info=True)
            return {
                "status": "degraded",
                "service": "MedChain AI",
                "modelo_disponible": False,
                "modelo_version": None,
            }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=9999, reload=True)
