"""Agregar columnas cifradas e indices ciegos a patients, tabla phi_access_log.

Revision ID: 002
Revises: 001
Create Date: 2026-08-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columnas cifradas (TEXT con formato v1:version:nonce:ct)
    op.add_column("patients", sa.Column("first_name_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("last_name_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("birth_date_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("gender_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("provider_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("provider_id_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("credential_id_enc", sa.Text(), nullable=True))
    op.add_column("patients", sa.Column("treatment_enc", sa.Text(), nullable=True))

    # Indices ciegos (BYTEA, 32 bytes HMAC-SHA256)
    op.add_column("patients", sa.Column("first_name_bidx", sa.LargeBinary(), nullable=True))
    op.add_column("patients", sa.Column("last_name_bidx", sa.LargeBinary(), nullable=True))
    op.add_column("patients", sa.Column("birth_date_bidx", sa.LargeBinary(), nullable=True))

    op.create_index("ix_patients_last_name_bidx", "patients", ["last_name_bidx"])
    op.create_index("ix_patients_first_name_bidx", "patients", ["first_name_bidx"])

    # Constraint anti-duplicado usando indices ciegos
    op.create_unique_constraint(
        "uq_patients_name_dob_bidx",
        "patients",
        ["last_name_bidx", "first_name_bidx", "birth_date_bidx"],
    )

    # Tabla de acceso a PHI
    op.create_table(
        "phi_access_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.VARCHAR(100), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.VARCHAR(50), nullable=False),
        sa.Column("fields_accessed", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_phi_access_log_patient_id", "phi_access_log", ["patient_id"])
    op.create_index("ix_phi_access_log_created_at", "phi_access_log", ["created_at"])

    # Tabla de tokens de nombre para busqueda por palabra
    op.create_table(
        "patient_name_tokens",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("patient_id", sa.BigInteger(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("token_bidx", sa.LargeBinary(), nullable=False),
    )
    op.create_index("ix_patient_name_tokens_bidx", "patient_name_tokens", ["token_bidx"])


def downgrade() -> None:
    op.drop_table("patient_name_tokens")
    op.drop_table("phi_access_log")
    op.drop_constraint("uq_patients_name_dob_bidx", "patients", type_="unique")
    op.drop_index("ix_patients_first_name_bidx", "patients")
    op.drop_index("ix_patients_last_name_bidx", "patients")
    for col in ["first_name_enc", "last_name_enc", "birth_date_enc", "gender_enc",
                "provider_enc", "provider_id_enc", "credential_id_enc", "treatment_enc",
                "first_name_bidx", "last_name_bidx", "birth_date_bidx"]:
        op.drop_column("patients", col)
