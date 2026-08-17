"""Router de salud detallada del sistema (pantalla del super admin)."""

from fastapi import APIRouter, Header

from backend.auth_middleware import require_auth, require_role

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def system_health(authorization: str | None = Header(default=None)):
    """Estado detallado: base de datos, modelo ML, puente Fabric y peers."""
    user = require_auth(authorization)
    require_role(user, ["super_admin"])

    from backend.blockchain.fabric_client import get_fabric_client
    from backend.db import is_db_available
    from backend.ml.model_loader import cargar_modelo, modelo_disponible

    artefacto = cargar_modelo()
    fabric = get_fabric_client().health()

    return {
        "database": "connected" if is_db_available() else "in-memory",
        "modelo_disponible": modelo_disponible(),
        "modelo_version": artefacto.get("version_modelo") if artefacto else None,
        "fabric_gateway": fabric if fabric is not None else {"status": "down"},
    }
