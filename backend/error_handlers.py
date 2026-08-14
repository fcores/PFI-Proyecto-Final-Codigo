"""
Manejo de errores centralizado — formato RFC 7807 (Problem Details).
Intercepta excepciones de dominio y genericas para respuestas uniformes
sin filtrar stack traces ni PHI al cliente.
"""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Excepcion base de dominio con status HTTP y tipo."""

    def __init__(self, detail: str, status_code: int = 400, error_type: str = "domain_error"):
        self.detail = detail
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(detail)


class NotFoundError(DomainError):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(detail, status_code=404, error_type="not_found")


class AuthorizationError(DomainError):
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(detail, status_code=403, error_type="forbidden")


class ConflictError(DomainError):
    def __init__(self, detail: str = "Conflicto"):
        super().__init__(detail, status_code=409, error_type="conflict")


def install_error_handlers(app: FastAPI) -> None:
    """Instala handlers globales de excepciones en la app FastAPI."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": exc.error_type,
                "title": exc.detail,
                "status": exc.status_code,
                "instance": str(request.url.path),
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        logger.error(
            "Error no manejado [%s]: %s",
            correlation_id,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": "internal_error",
                "title": "Error interno del servidor",
                "status": 500,
                "instance": str(request.url.path),
                "correlation_id": correlation_id,
            },
        )
