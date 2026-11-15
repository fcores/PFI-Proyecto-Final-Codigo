"""Converge el esquema al estado declarado en sql/schema.sql.

Revision ID: 004
Revises: 003
Create Date: 2026-08-15

Esta revision es 100% idempotente y re-afirma el estado final completo. Corre
incluso sobre bases ya stampeadas en 003, de modo que cubre cualquier
divergencia historica (por ejemplo, una RDS que quedo stampeada sin haber
aplicado realmente la DDL, o una anterior a sql/migrations/*.sql, que nunca
tuvieron runner).

INVARIANTE: todo lo que se agregue aca tiene que estar tambien en
sql/schema.sql, y viceversa. El test tests/test_schema_drift.py verifica que
'alembic upgrade head' sobre una base recien creada con schema.sql no produzca
ningun cambio.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS prescription_id_seq START WITH 1 INCREMENT BY 1")
    op.execute("""
DO $$
BEGIN
    IF to_regclass('public.prescriptions') IS NULL THEN
        RAISE NOTICE '004: DB vacia, se omite (sql/schema.sql crea el estado final)';
        RETURN;
    END IF;

    -- DDL nueva de esta revision:
    -- updated_at la escribe backend/blockchain/outbox_worker.py y no existia en
    -- ninguna revision previa ni en schema.sql.
    -- costo_por_farmaco / costo_total las lee el detalle de auditoria.
    ALTER TABLE prescriptions
        ADD COLUMN IF NOT EXISTS updated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
        ADD COLUMN IF NOT EXISTS costo_por_farmaco TEXT DEFAULT '[]',
        ADD COLUMN IF NOT EXISTS costo_total       NUMERIC(14,2);

    -- Re-afirmacion de 003
    ALTER TABLE prescriptions
        ADD COLUMN IF NOT EXISTS estado_commit VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        ADD COLUMN IF NOT EXISTS tx_id         VARCHAR(256),
        ADD COLUMN IF NOT EXISTS block_number  INTEGER,
        ADD COLUMN IF NOT EXISTS payload_hash  VARCHAR(64);

    -- Re-afirmacion de 002
    ALTER TABLE patients
        ADD COLUMN IF NOT EXISTS first_name_enc    TEXT,
        ADD COLUMN IF NOT EXISTS last_name_enc     TEXT,
        ADD COLUMN IF NOT EXISTS birth_date_enc    TEXT,
        ADD COLUMN IF NOT EXISTS gender_enc        TEXT,
        ADD COLUMN IF NOT EXISTS provider_enc      TEXT,
        ADD COLUMN IF NOT EXISTS provider_id_enc   TEXT,
        ADD COLUMN IF NOT EXISTS credential_id_enc TEXT,
        ADD COLUMN IF NOT EXISTS treatment_enc     TEXT,
        ADD COLUMN IF NOT EXISTS first_name_bidx   BYTEA,
        ADD COLUMN IF NOT EXISTS last_name_bidx    BYTEA,
        ADD COLUMN IF NOT EXISTS birth_date_bidx   BYTEA;

    -- Maestros: absorbe sql/migrations/001 y 003, que nunca tuvieron runner
    ALTER TABLE medications
        ADD COLUMN IF NOT EXISTS codigo             VARCHAR(100),
        ADD COLUMN IF NOT EXISTS laboratorio        VARCHAR(300),
        ADD COLUMN IF NOT EXISTS monodroga          VARCHAR(200),
        ADD COLUMN IF NOT EXISTS potencia_mg        NUMERIC(12,4),
        ADD COLUMN IF NOT EXISTS unidad_potencia    VARCHAR(50),
        ADD COLUMN IF NOT EXISTS precio             NUMERIC(14,2),
        ADD COLUMN IF NOT EXISTS via_administracion VARCHAR(100);
    ALTER TABLE monodrugs
        ADD COLUMN IF NOT EXISTS codigo VARCHAR(100);

    CREATE INDEX IF NOT EXISTS ix_prescriptions_patient_id    ON prescriptions(patient_id);
    CREATE INDEX IF NOT EXISTS ix_prescriptions_estado_commit ON prescriptions(estado_commit);
    CREATE INDEX IF NOT EXISTS ix_patients_last_name_bidx     ON patients(last_name_bidx);
    CREATE INDEX IF NOT EXISTS ix_patients_first_name_bidx    ON patients(first_name_bidx);
END $$;
""")


def downgrade() -> None:
    raise NotImplementedError("Downgrade no soportado: reconciliacion forward-only")
