"""Crear tabla prescription_outbox para patron outbox con idempotencia.

Revision ID: 003
Revises: 002
Create Date: 2026-08-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columnas de estado de commit a prescriptions
    op.add_column("prescriptions", sa.Column(
        "estado_commit", sa.VARCHAR(20), server_default="pendiente", nullable=False
    ))
    op.add_column("prescriptions", sa.Column("tx_id", sa.VARCHAR(256), nullable=True))
    op.add_column("prescriptions", sa.Column("block_number", sa.Integer(), nullable=True))
    op.add_column("prescriptions", sa.Column("payload_hash", sa.VARCHAR(64), nullable=True))

    op.create_index("ix_prescriptions_estado_commit", "prescriptions", ["estado_commit"])

    # Tabla outbox para encolar commits pendientes a Fabric
    op.create_table(
        "prescription_outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("prescription_id", sa.BigInteger(), sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("idempotency_key", sa.VARCHAR(100), unique=True, nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.VARCHAR(20), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_outbox_status", "prescription_outbox", ["status"])


def downgrade() -> None:
    op.drop_table("prescription_outbox")
    op.drop_index("ix_prescriptions_estado_commit", "prescriptions")
    op.drop_column("prescriptions", "payload_hash")
    op.drop_column("prescriptions", "block_number")
    op.drop_column("prescriptions", "tx_id")
    op.drop_column("prescriptions", "estado_commit")
