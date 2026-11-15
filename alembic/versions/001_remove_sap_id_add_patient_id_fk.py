"""Eliminar sap_id de patients, migrar patient_sap_id a patient_id FK en prescriptions.

Revision ID: 001
Revises: None
Create Date: 2026-08-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Idempotente: no-op si la base ya tiene la forma nueva (sql/schema.sql) o si esta vacia."""
    op.execute("CREATE SEQUENCE IF NOT EXISTS prescription_id_seq START WITH 1 INCREMENT BY 1")
    op.execute("""
DO $$
BEGIN
    IF to_regclass('public.prescriptions') IS NULL OR to_regclass('public.patients') IS NULL THEN
        RAISE NOTICE '001: tablas base ausentes (DB vacia), se omite';
        RETURN;
    END IF;

    -- Paso 1: columna patient_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'prescriptions'
                     AND column_name = 'patient_id') THEN
        ALTER TABLE prescriptions ADD COLUMN patient_id BIGINT;
    END IF;

    -- Paso 2: backfill desde el modelo legacy, solo si ambas columnas legacy existen
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'prescriptions'
                 AND column_name = 'patient_sap_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'patients'
                     AND column_name = 'sap_id') THEN
        EXECUTE '
            UPDATE prescriptions p SET patient_id = pat.id
            FROM patients pat
            WHERE p.patient_sap_id = pat.sap_id AND p.patient_id IS NULL';
    END IF;

    -- Paso 3: NOT NULL solo si no quedan huerfanas
    IF EXISTS (SELECT 1 FROM prescriptions WHERE patient_id IS NULL) THEN
        RAISE WARNING '001: hay prescripciones sin patient_id; se dejan NULL y NO se aplica NOT NULL';
    ELSE
        ALTER TABLE prescriptions ALTER COLUMN patient_id SET NOT NULL;
    END IF;

    -- Paso 4: FK solo si no existe ya alguna sobre patient_id.
    -- sql/schema.sql la declara inline, por eso no alcanza con buscar el nombre.
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
        WHERE c.contype = 'f'
          AND c.conrelid = 'public.prescriptions'::regclass
          AND a.attname = 'patient_id'
    ) THEN
        ALTER TABLE prescriptions
            ADD CONSTRAINT fk_prescriptions_patient_id
            FOREIGN KEY (patient_id) REFERENCES patients(id);
    END IF;

    CREATE INDEX IF NOT EXISTS ix_prescriptions_patient_id ON prescriptions(patient_id);

    -- Paso 5: columnas legacy
    ALTER TABLE prescriptions DROP COLUMN IF EXISTS patient_sap_id;
    ALTER TABLE patients DROP COLUMN IF EXISTS sap_id;
END $$;
""")


def downgrade() -> None:
    raise NotImplementedError("Downgrade no soportado: reconciliacion forward-only")
