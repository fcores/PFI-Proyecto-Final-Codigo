"""Rol financiador en el CHECK de users (RF-40).

Revision ID: 009
Revises: 008
Create Date: 2026-10-17

- Amplia chk_users_role con el rol financiador, que accede al panel de lectura
  del financiador y lee de Fabric con la identidad de PrepagaMSP.

El DDL vive en sql/migration_009_rol_financiador.sql. 100% idempotente.
Espejo de sql/schema.sql.
"""

import logging
from pathlib import Path
from typing import Sequence, Union

from alembic import op
from backend.db import load_query

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)

_ARCHIVO_SQL = Path("migration_009_rol_financiador.sql")


def upgrade() -> None:
    """Agrega el rol financiador a la restriccion de roles."""
    try:
        op.execute(load_query(str(_ARCHIVO_SQL))["upgrade"])
    except Exception as exc:
        logger.error("Error en la migracion 009 (upgrade): %s", exc, exc_info=True)
        raise


def downgrade() -> None:
    """Quita el rol financiador de la restriccion de roles."""
    try:
        op.execute(load_query(str(_ARCHIVO_SQL))["downgrade"])
    except Exception as exc:
        logger.error("Error en la migracion 009 (downgrade): %s", exc, exc_info=True)
        raise
