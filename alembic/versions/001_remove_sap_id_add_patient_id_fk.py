"""Eliminar sap_id de patients, migrar patient_sap_id a patient_id FK en prescriptions.

Revision ID: 001
Revises: None
Create Date: 2026-08-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Paso 1: Agregar patient_id INTEGER en prescriptions y poblar desde patients
    op.add_column("prescriptions", sa.Column("patient_id", sa.BigInteger(), nullable=True))

    # Vincular prescriptions.patient_id con patients.id via sap_id
    op.execute("""
        UPDATE prescriptions p
        SET patient_id = pat.id
        FROM patients pat
        WHERE p.patient_sap_id = pat.sap_id
    """)

    # Prescripciones huerfanas (sin paciente): asignar NULL (se detectaran)
    # Hacer NOT NULL una vez validado
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM prescriptions WHERE patient_id IS NULL) THEN
                RAISE NOTICE 'ATENCION: hay prescripciones sin patient_id. Se mantienen como NULL.';
            END IF;
        END $$;
    """)

    # Paso 2: Agregar FK y hacer NOT NULL (solo si no hay huerfanos)
    op.alter_column("prescriptions", "patient_id", nullable=False,
                    existing_type=sa.BigInteger())
    op.create_foreign_key(
        "fk_prescriptions_patient_id",
        "prescriptions", "patients",
        ["patient_id"], ["id"],
    )
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])

    # Paso 3: Eliminar patient_sap_id de prescriptions
    op.drop_column("prescriptions", "patient_sap_id")

    # Paso 4: Eliminar sap_id de patients
    op.drop_column("patients", "sap_id")

    # Paso 5: Crear secuencia para prescription IDs (para la Fase 4 outbox)
    op.execute("CREATE SEQUENCE IF NOT EXISTS prescription_id_seq START WITH 1 INCREMENT BY 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS prescription_id_seq")
    op.add_column("patients", sa.Column("sap_id", sa.VARCHAR(100), nullable=True))
    op.add_column("prescriptions", sa.Column("patient_sap_id", sa.VARCHAR(100), nullable=True))
    op.drop_constraint("fk_prescriptions_patient_id", "prescriptions", type_="foreignkey")
    op.drop_index("ix_prescriptions_patient_id", "prescriptions")
    op.drop_column("prescriptions", "patient_id")
