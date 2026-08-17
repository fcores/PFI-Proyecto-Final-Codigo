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
    health_router,
    medication_router,
    monodrug_router,
    patient_router,
    prescription_router,
    user_router,
)
from backend.security.phi_redactor import install_phi_filter

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Crea y configura la instancia FastAPI con routers bajo /api."""
    settings = get_settings()
    install_phi_filter()

    app = FastAPI(title="MedChain AI", version="0.8.0")
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()

    from backend.db import is_db_available

    if not is_db_available():
        logger.warning(
            "MODO IN-MEMORY ACTIVO (solo desarrollo): sin cifrado PHI, sin UNIQUE constraints, "
            "sin phi_access_log ni gestion de usuarios. Configurar DATABASE_URL para produccion.",
        )
        if settings.is_production:
            raise RuntimeError("DATABASE_URL es obligatoria en produccion")

    if not settings.fabric_gateway_url:
        logger.warning(
            "FABRIC_GATEWAY_URL no configurada: las operaciones de prescripciones "
            "fallaran con 503. Las prescripciones viven exclusivamente en Fabric.",
        )

    api = APIRouter(prefix="/api")
    api.include_router(patient_router)
    api.include_router(medication_router)
    api.include_router(monodrug_router)
    api.include_router(prescription_router)
    api.include_router(auth_router)
    api.include_router(audit_router)
    api.include_router(user_router)
    api.include_router(health_router)
    app.include_router(api)

    @app.get("/")
    async def root():
        """Health check: estado del modelo ML, la base de datos y el puente Fabric."""
        from backend.db import is_db_available

        try:
            artefacto = cargar_modelo()
            version = artefacto.get("version_modelo") if artefacto else None

            fabric_status = "not_configured"
            if settings.fabric_gateway_url:
                from backend.dependencies import get_fabric_client

                health = get_fabric_client().health()
                fabric_status = health.get("status", "down") if health else "down"

            return {
                "status": "ok",
                "service": "MedChain AI",
                "database": "connected" if is_db_available() else "in-memory",
                "modelo_disponible": modelo_disponible(),
                "modelo_version": version,
                "fabric_gateway": fabric_status,
            }
        except Exception as exc:
            logger.error("Error en health check root: %s", exc, exc_info=True)
            return {
                "status": "degraded",
                "service": "MedChain AI",
                "modelo_disponible": False,
                "modelo_version": None,
                "fabric_gateway": "unknown",
            }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=9999, reload=True)
