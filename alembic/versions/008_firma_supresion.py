"""Firma electronica de prescriptores y supresion de datos (RF-35 a RF-39).

Revision ID: 008
Revises: 007
Create Date: 2026-10-17

- user_signing_keys: par de claves ECDSA P-256 por prescriptor (privada cifrada).
- users.anonymized_at / patients.anonymized_at: marca de anonimizacion.
- patient_suppression_requests: solicitudes de supresion con guarda de retencion.

El DDL vive en sql/migration_008_firma_supresion.sql. 100% idempotente.
Espejo de sql/schema.sql.
"""

import logging
from pathlib import Path
from typing import Sequence, Union

from alembic import op
from backend.db import load_query

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)

_ARCHIVO_SQL = Path("migration_008_firma_supresion.sql")


def upgrade() -> None:
    """Crea las tablas y columnas de firma y supresion."""
    try:
        op.execute(load_query(str(_ARCHIVO_SQL))["upgrade"])
    except Exception as exc:
        logger.error("Error en la migracion 008 (upgrade): %s", exc, exc_info=True)
        raise


def downgrade() -> None:
    """Revierte las tablas y columnas de firma y supresion."""
    try:
        op.execute(load_query(str(_ARCHIVO_SQL))["downgrade"])
    except Exception as exc:
        logger.error("Error en la migracion 008 (downgrade): %s", exc, exc_info=True)
        raise
