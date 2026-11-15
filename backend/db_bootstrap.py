"""
Bootstrap del esquema de base de datos, ejecutado antes de uvicorn (ver Dockerfile).

Orden:
  1. sql/schema.sql        -> crea los objetos que falten (base nueva). No altera tablas existentes.
  2. alembic upgrade head  -> converge una base preexistente al estado actual.

Seguro ante ejecucion concurrente (varias tasks de ECS durante un rolling deploy):
toma un advisory lock de PostgreSQL a nivel de sesion. Este es el UNICO lugar donde
se toma ese lock; no agregarlo tambien en alembic/env.py o las dos sesiones se
bloquean entre si.

Exit codes: 0 = ok, 1 = error. Un error deja el contenedor en crash loop a
proposito: es preferible a servir trafico contra un esquema roto.
"""

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Clave arbitraria pero estable del advisory lock de migraciones.
_MIGRATION_LOCK_KEY = 728405113

logger = logging.getLogger("db_bootstrap")


def _run_alembic_upgrade() -> None:
    """Ejecuta 'alembic upgrade head' en proceso."""
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(ROOT_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    command.upgrade(cfg, "head")


def main() -> int:
    """Aplica schema.sql y las migraciones. Retorna el exit code del proceso."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [db_bootstrap] %(message)s")

    from backend.config import get_settings

    settings = get_settings()
    if not settings.database_url:
        if settings.is_production:
            logger.error("DATABASE_URL ausente en produccion")
            return 1
        logger.info("DATABASE_URL no configurada: modo in-memory, no hay nada que migrar")
        return 0

    import psycopg2

    # Conexion dedicada (no del pool) y en autocommit: el advisory lock es de
    # sesion y debe sobrevivir a los commits que hacen schema.sql y alembic.
    lock_conn = psycopg2.connect(settings.database_url)
    lock_conn.autocommit = True
    try:
        with lock_conn.cursor() as cur:
            logger.info("Esperando advisory lock de migraciones...")
            cur.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK_KEY,))
        logger.info("Lock adquirido")

        from backend.db import init_db

        init_db()
        logger.info("sql/schema.sql aplicado")

        _run_alembic_upgrade()
        logger.info("alembic upgrade head aplicado")
        return 0
    except Exception as exc:
        logger.error("Fallo el bootstrap de base de datos: %s", exc, exc_info=True)
        return 1
    finally:
        try:
            with lock_conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK_KEY,))
        except Exception as exc:
            # Cerrar la conexion libera el lock igual; solo dejamos rastro.
            logger.warning("No se pudo liberar el advisory lock: %s", exc)
        lock_conn.close()


if __name__ == "__main__":
    sys.exit(main())
