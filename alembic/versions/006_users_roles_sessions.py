"""Rol super_admin en el CHECK de users + tabla auth_tokens (sesiones persistentes).

Revision ID: 006
Revises: 005
Create Date: 2026-08-17

- Amplia chk_users_role a los 4 roles: administrador, prescriptor, auditor,
  super_admin (el usuario inicial superadmin lo siembra AuthService).
- Crea auth_tokens: sesiones con token hasheado SHA-256 y expiracion, para que
  el login sobreviva reinicios y multiples replicas del backend.

100% idempotente. Todo lo que se agrega aca esta reflejado en sql/schema.sql
(invariante verificada por tests/test_schema_drift.py).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
DO $$
BEGIN
    IF to_regclass('public.users') IS NOT NULL THEN
        ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
        ALTER TABLE users ADD CONSTRAINT chk_users_role
            CHECK (role IN ('administrador', 'prescriptor', 'auditor', 'super_admin'));
    END IF;
END $$;
""")

    op.execute("""
CREATE TABLE IF NOT EXISTS auth_tokens (
    token_hash CHAR(64) PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);
""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_tokens_expires_at ON auth_tokens(expires_at);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_tokens;")
    op.execute("""
DO $$
BEGIN
    IF to_regclass('public.users') IS NOT NULL THEN
        ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
        ALTER TABLE users ADD CONSTRAINT chk_users_role
            CHECK (role IN ('administrador', 'prescriptor', 'auditor'));
    END IF;
END $$;
""")
