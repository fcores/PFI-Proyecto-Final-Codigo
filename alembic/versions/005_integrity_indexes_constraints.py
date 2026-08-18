"""Agrega FKs, indices, CHECK constraints, UNIQUE constraints, JSONB y mejoras de esquema.

Revision ID: 005
Revises: 004
Create Date: 2026-08-16

Cubre las recomendaciones P1-fks, P2-jsonb, P2-checks, P2-indexes del plan de mejoras.
100% idempotente: usa IF NOT EXISTS / ADD COLUMN IF NOT EXISTS / DO $$ bloques.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
DO $$
BEGIN
    IF to_regclass('public.prescriptions') IS NULL THEN
        RAISE NOTICE '005: DB vacia, se omite (sql/schema.sql crea el estado final)';
        RETURN;
    END IF;

    -- =====================================================================
    -- P1: Foreign keys con ON DELETE explicito
    -- =====================================================================

    -- audit_cases.assigned_auditor -> users.username
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_cases_auditor'
    ) THEN
        -- Solo agregar la FK si todos los valores actuales existen en users
        IF NOT EXISTS (
            SELECT 1 FROM audit_cases ac
            WHERE ac.assigned_auditor IS NOT NULL
              AND ac.assigned_auditor NOT IN (SELECT username FROM users)
        ) THEN
            ALTER TABLE audit_cases
                ADD CONSTRAINT fk_audit_cases_auditor
                FOREIGN KEY (assigned_auditor) REFERENCES users(username) ON DELETE SET NULL;
        ELSE
            RAISE WARNING '005: audit_cases tiene assigned_auditor huerfanos, no se crea FK';
        END IF;
    END IF;

    -- dictamenes.auditor_username -> users.username
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_dictamenes_auditor'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM dictamenes d
            WHERE d.auditor_username NOT IN (SELECT username FROM users)
        ) THEN
            ALTER TABLE dictamenes
                ADD CONSTRAINT fk_dictamenes_auditor
                FOREIGN KEY (auditor_username) REFERENCES users(username) ON DELETE RESTRICT;
        ELSE
            RAISE WARNING '005: dictamenes tiene auditor_username huerfanos, no se crea FK';
        END IF;
    END IF;

    -- corrections.auditor_username -> users.username
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_corrections_auditor'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM corrections c
            WHERE c.auditor_username NOT IN (SELECT username FROM users)
        ) THEN
            ALTER TABLE corrections
                ADD CONSTRAINT fk_corrections_auditor
                FOREIGN KEY (auditor_username) REFERENCES users(username) ON DELETE RESTRICT;
        ELSE
            RAISE WARNING '005: corrections tiene auditor_username huerfanos, no se crea FK';
        END IF;
    END IF;

    -- =====================================================================
    -- P2: Indices faltantes en FKs y filtros frecuentes
    -- =====================================================================
    CREATE INDEX IF NOT EXISTS ix_audit_cases_prescription_id ON audit_cases(prescription_id);
    CREATE INDEX IF NOT EXISTS ix_audit_cases_status ON audit_cases(status);
    CREATE INDEX IF NOT EXISTS ix_dictamenes_audit_case_id ON dictamenes(audit_case_id);
    CREATE INDEX IF NOT EXISTS ix_corrections_audit_case_id ON corrections(audit_case_id);
    CREATE INDEX IF NOT EXISTS ix_outbox_prescription_id ON prescription_outbox(prescription_id);
    CREATE INDEX IF NOT EXISTS ix_patient_name_tokens_patient_id ON patient_name_tokens(patient_id);

    -- =====================================================================
    -- P2: CHECK constraints en campos categoricos
    -- =====================================================================
    -- Esta migracion es anterior al rol super_admin (lo agrega la 006). Una base
    -- que ya tenga usuarios super_admin sembrados viola este CHECK y la
    -- migracion aborta entera. Se aplica el mismo criterio defensivo que en las
    -- FKs de mas arriba: si hay filas que no encajan, se omite y sigue.
    -- La 006 hace DROP + CREATE de esta misma constraint con los 4 roles.
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_role') THEN
        IF NOT EXISTS (
            SELECT 1 FROM users
            WHERE role NOT IN ('administrador', 'prescriptor', 'auditor')
        ) THEN
            ALTER TABLE users ADD CONSTRAINT chk_users_role
                CHECK (role IN ('administrador', 'prescriptor', 'auditor'));
        ELSE
            RAISE WARNING '005: users tiene roles fuera del set de esta migracion; la 006 crea el CHECK definitivo';
        END IF;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_prescriptions_msi') THEN
        ALTER TABLE prescriptions ADD CONSTRAINT chk_prescriptions_msi
            CHECK (msi IN ('MSI-H', 'MSS', 'no_evaluado'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_prescriptions_ras') THEN
        ALTER TABLE prescriptions ADD CONSTRAINT chk_prescriptions_ras
            CHECK (ras IN ('wild_type', 'mutado', 'no_evaluado'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_prescriptions_braf') THEN
        ALTER TABLE prescriptions ADD CONSTRAINT chk_prescriptions_braf
            CHECK (braf_v600e IN ('presente', 'wild_type', 'no_evaluado'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_prescriptions_estado_validacion') THEN
        ALTER TABLE prescriptions ADD CONSTRAINT chk_prescriptions_estado_validacion
            CHECK (estado_validacion IN ('APROBADO', 'RECHAZADO', 'REVISION', 'APROBADO_AUDITORIA', 'RECHAZADO_AUDITORIA'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_prescriptions_estado_commit') THEN
        ALTER TABLE prescriptions ADD CONSTRAINT chk_prescriptions_estado_commit
            CHECK (estado_commit IN ('pendiente', 'confirmado', 'fallido'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_audit_cases_status') THEN
        ALTER TABLE audit_cases ADD CONSTRAINT chk_audit_cases_status
            CHECK (status IN ('pendiente', 'en_revision', 'dictaminado'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_dictamenes_resultado') THEN
        ALTER TABLE dictamenes ADD CONSTRAINT chk_dictamenes_resultado
            CHECK (resultado IN ('aprobado', 'rechazado'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_outbox_status') THEN
        ALTER TABLE prescription_outbox ADD CONSTRAINT chk_outbox_status
            CHECK (status IN ('pending', 'processing', 'committed', 'failed', 'dead_letter'));
    END IF;

    -- =====================================================================
    -- P2: UNIQUE constraints en claves de negocio
    -- =====================================================================
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_monodrugs_codigo') THEN
        ALTER TABLE monodrugs ADD CONSTRAINT uq_monodrugs_codigo UNIQUE (codigo);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_prescriptions_code') THEN
        ALTER TABLE prescriptions ADD CONSTRAINT uq_prescriptions_code UNIQUE (prescription_code);
    END IF;

    -- =====================================================================
    -- P2: Migrar columnas TEXT con JSON a JSONB
    --
    -- Las columnas tienen DEFAULT '[]'::text. Postgres NO castea el default
    -- automaticamente al cambiar el tipo y aborta con:
    --   default for column "..." cannot be cast automatically to type jsonb
    -- Por eso hay que soltar el default, cambiar el tipo y reponerlo ya en JSONB.
    -- =====================================================================
    ALTER TABLE prescriptions
        ALTER COLUMN dosis_por_farmaco DROP DEFAULT,
        ALTER COLUMN motivos_validacion DROP DEFAULT,
        ALTER COLUMN features_relevantes DROP DEFAULT,
        ALTER COLUMN costo_por_farmaco DROP DEFAULT;

    ALTER TABLE prescriptions
        ALTER COLUMN dosis_por_farmaco TYPE JSONB USING dosis_por_farmaco::jsonb,
        ALTER COLUMN motivos_validacion TYPE JSONB USING motivos_validacion::jsonb,
        ALTER COLUMN features_relevantes TYPE JSONB USING features_relevantes::jsonb,
        ALTER COLUMN costo_por_farmaco TYPE JSONB USING costo_por_farmaco::jsonb;

    ALTER TABLE prescriptions
        ALTER COLUMN dosis_por_farmaco SET DEFAULT '[]'::jsonb,
        ALTER COLUMN motivos_validacion SET DEFAULT '[]'::jsonb,
        ALTER COLUMN features_relevantes SET DEFAULT '[]'::jsonb,
        ALTER COLUMN costo_por_farmaco SET DEFAULT '[]'::jsonb;

    ALTER TABLE patients ALTER COLUMN medications DROP DEFAULT;
    ALTER TABLE patients
        ALTER COLUMN medications TYPE JSONB USING medications::jsonb;
    ALTER TABLE patients ALTER COLUMN medications SET DEFAULT '[]'::jsonb;

    -- =====================================================================
    -- P2: ledger_blocks.timestamp a TIMESTAMPTZ
    -- =====================================================================
    ALTER TABLE ledger_blocks
        ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp::timestamptz;

END $$;
""")


def downgrade() -> None:
    raise NotImplementedError("Downgrade no soportado: reconciliacion forward-only")
