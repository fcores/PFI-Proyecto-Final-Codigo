"""
Alembic env.py — ejecuta migraciones contra la base de datos.
Lee DATABASE_URL desde la variable de entorno (o .env via pydantic-settings).
"""
import logging
import os
import sys
from logging.config import fileConfig

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = context.config
if config.config_file_name is not None:
    # Sin disable_existing_loggers=False se silencia el logger de
    # backend/db_bootstrap.py y un fallo de migracion sale sin traceback.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

logger = logging.getLogger("alembic.env")

target_metadata = None


def get_url() -> str:
    """Obtiene la URL de la base de datos desde el entorno, forzando el driver psycopg2."""
    try:
        url = os.getenv("DATABASE_URL")
        if not url:
            from backend.config import get_settings
            settings = get_settings()
            url = settings.database_url
        if not url:
            raise RuntimeError(
                "DATABASE_URL no configurada. Las migraciones requieren una base de datos."
            )
        # SQLAlchemy 2.1 resuelve 'postgresql://' a psycopg (v3), que no esta
        # instalado; el proyecto usa psycopg2.
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        elif url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        return url
    except Exception as exc:
        logger.error("No se pudo resolver DATABASE_URL: %s", exc, exc_info=True)
        raise


def run_migrations_offline() -> None:
    """Genera SQL sin conectar a la base."""
    try:
        url = get_url()
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
    except Exception as exc:
        logger.error("Fallo la migracion offline: %s", exc, exc_info=True)
        raise


def run_migrations_online() -> None:
    """Ejecuta migraciones contra la base conectada.

    transaction_per_migration=True: cada revision commitea por separado, de modo
    que un fallo en la revision N deja aplicadas 1..N-1 con alembic_version
    coherente y el proceso es reintentable.

    El lock de exclusion mutua entre tasks de ECS lo toma backend/db_bootstrap.py;
    no agregarlo aca tambien o las dos sesiones se bloquean entre si.
    """
    try:
        from sqlalchemy import create_engine, pool

        url = get_url()
        connectable = create_engine(url, poolclass=pool.NullPool)

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                transaction_per_migration=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    except Exception as exc:
        logger.error("Fallo la migracion online: %s", exc, exc_info=True)
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
