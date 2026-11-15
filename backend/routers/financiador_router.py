"""Router del panel de lectura del financiador (RF-40).

Solo lectura. Acceden el financiador y el super admin; los datos se leen de
Fabric con la identidad de PrepagaMSP.
"""

import logging

from fastapi import APIRouter, Header, Query

from backend.auth_middleware import require_auth, require_role
from backend.dependencies import get_financiador_service
from backend.models.financiador import ExpedientesFinanciador, ResumenFinanciador

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financiador", tags=["financiador"])

_ROLES_FINANCIADOR = ["financiador", "super_admin"]


def resumen_financiador(authorization: str | None = Header(default=None)) -> ResumenFinanciador:
    """Indicadores agregados de las palancas de costo evitado."""
    try:
        user = require_auth(authorization)
        require_role(user, _ROLES_FINANCIADOR)
        return get_financiador_service().resumen()
    except Exception as exc:
        logger.warning("No se pudo obtener el resumen del financiador: %s", exc)
        raise


def expedientes_financiador(
    surge: bool | None = Query(None, description="Solo potencialmente recuperables ante el SURGE"),
    plazo: str | None = Query(None, description="en_plazo, por_vencer, vencido, cumplido o cumplido_fuera_de_plazo"),
    alternativa: str | None = Query(None, description="alerta o adoptada"),
    authorization: str | None = Header(default=None),
) -> ExpedientesFinanciador:
    """Expedientes del panel, sin datos clinicos de detalle."""
    try:
        user = require_auth(authorization)
        require_role(user, _ROLES_FINANCIADOR)
        return get_financiador_service().expedientes(surge=surge, plazo=plazo, alternativa=alternativa)
    except Exception as exc:
        logger.warning("No se pudieron listar los expedientes del financiador: %s", exc)
        raise


router.add_api_route(
    "/resumen",
    resumen_financiador,
    methods=["GET"],
    response_model=ResumenFinanciador,
)
router.add_api_route(
    "/expedientes",
    expedientes_financiador,
    methods=["GET"],
    response_model=ExpedientesFinanciador,
)
