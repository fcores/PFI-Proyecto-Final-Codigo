"""Retira las prescripciones (y su auditoria) de la RDS: viven solo en Fabric.

Revision ID: 007
Revises: 006
Create Date: 2026-08-17

La prescripcion contiene datos clinicos sensibles y su fuente de verdad pasa a
ser exclusivamente el world state de Hyperledger Fabric (chaincode
`prescriptions`, red de 3 organizaciones con endorsement AND). Se eliminan:

- prescriptions, audit_cases, dictamenes, corrections (flujo off-chain)
- ledger_blocks (ledger interno SHA-256, reemplazado por Fabric)
- prescription_outbox (el alta pasa a ser sincrona)
- prescription_id_seq (el ID ahora es un ULID generado por el backend)
- patients.blockchain_tx_id (columna del ledger interno, sin uso)

ATENCION: las prescripciones existentes en la RDS NO se migran a Fabric. Si
hace falta conservarlas, correr scripts/backfill (opcional) ANTES de aplicar
esta migracion.

100% idempotente (DROP IF EXISTS). Espejo de sql/schema.sql.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
DROP TABLE IF EXISTS prescription_outbox CASCADE;
DROP TABLE IF EXISTS corrections CASCADE;
DROP TABLE IF EXISTS dictamenes CASCADE;
DROP TABLE IF EXISTS audit_cases CASCADE;
DROP TABLE IF EXISTS ledger_blocks CASCADE;
DROP TABLE IF EXISTS prescriptions CASCADE;
DROP SEQUENCE IF EXISTS prescription_id_seq;
""")
    op.execute("""
DO $$
BEGIN
    IF to_regclass('public.patients') IS NOT NULL THEN
        ALTER TABLE patients DROP COLUMN IF EXISTS blockchain_tx_id;
    END IF;
END $$;
""")


def downgrade() -> None:
    # Irreversible: los datos eliminados no se pueden reconstruir desde la RDS.
    # El estado anterior del esquema lo recrean las migraciones 001-005.
    raise NotImplementedError("007 es irreversible: las prescripciones viven en Fabric")
