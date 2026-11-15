"""Verifica que sql/schema.sql y las migraciones de Alembic describan el mismo esquema.

El invariante: sobre una base creada con sql/schema.sql, 'alembic upgrade head'
no debe producir ningun cambio. Si alguien agrega una columna en un solo lado,
estos tests rompen.

Requieren un PostgreSQL real. Se saltean si no hay TEST_DATABASE_URL.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL no configurada (se requiere un PostgreSQL real)",
)


def _connect():
    import psycopg2

    return psycopg2.connect(TEST_DATABASE_URL)


def _reset_schema() -> None:
    """Deja la base vacia."""
    conn = _connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    finally:
        conn.close()


def _apply_schema_sql() -> None:
    """Aplica sql/schema.sql tal como lo hace backend.db.init_db()."""
    sql = (ROOT_DIR / "sql" / "schema.sql").read_text(encoding="utf-8")
    conn = _connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def _alembic_upgrade_head() -> None:
    env = dict(os.environ, DATABASE_URL=TEST_DATABASE_URL)
    result = subprocess.run(  # noqa: S603
        ["alembic", "upgrade", "head"],  # noqa: S607
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "alembic upgrade head fallo:\n%s\n%s" % (
        result.stdout,
        result.stderr,
    )


def _snapshot() -> dict:
    """Devuelve columnas, indices y constraints del schema public."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name, column_name, data_type,
                       COALESCE(character_maximum_length, -1), is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name <> 'alembic_version'
                ORDER BY 1, 2
                """)
            columns = cur.fetchall()

            cur.execute("""
                SELECT tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename <> 'alembic_version'
                ORDER BY 1, 2
                """)
            indexes = cur.fetchall()

            cur.execute("""
                SELECT c.conrelid::regclass::text, c.contype::text, pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public' AND t.relname <> 'alembic_version'
                ORDER BY 1, 2, 3
                """)
            constraints = cur.fetchall()
        return {"columns": columns, "indexes": indexes, "constraints": constraints}
    finally:
        conn.close()


def test_alembic_no_modifica_una_base_creada_con_schema_sql():
    """schema.sql y las migraciones describen el mismo estado final."""
    _reset_schema()
    _apply_schema_sql()
    antes = _snapshot()

    _alembic_upgrade_head()
    despues = _snapshot()

    assert (
        despues["columns"] == antes["columns"]
    ), "Drift de columnas entre sql/schema.sql y alembic/versions.\n" "Solo en Alembic: %s\nSolo en schema.sql: %s" % (
        sorted(set(despues["columns"]) - set(antes["columns"])),
        sorted(set(antes["columns"]) - set(despues["columns"])),
    )
    assert despues["indexes"] == antes["indexes"], "Drift de indices"
    assert despues["constraints"] == antes["constraints"], "Drift de constraints"


def test_alembic_converge_una_base_vacia():
    """Sobre una base vacia, las migraciones no explotan y llegan a head."""
    _reset_schema()
    _alembic_upgrade_head()
    _alembic_upgrade_head()  # idempotente: correrlo dos veces no debe fallar


def test_alembic_es_idempotente_sobre_schema_sql():
    """Correr upgrade head dos veces seguidas no falla ni cambia nada."""
    _reset_schema()
    _apply_schema_sql()
    _alembic_upgrade_head()
    primera = _snapshot()

    _alembic_upgrade_head()
    segunda = _snapshot()

    assert segunda == primera, "La segunda corrida de alembic upgrade head cambio el esquema"
