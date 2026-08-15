"""
Alembic env.py — ejecuta migraciones contra la base de datos.
Lee DATABASE_URL desde la variable de entorno (o .env via pydantic-settings).
"""
import os
import sys
from logging.config import fileConfig

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    """Obtiene la URL de la base de datos desde el entorno."""
    url = os.getenv("DATABASE_URL")
    if not url:
        from backend.config import get_settings
        settings = get_settings()
        url = settings.database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL no configurada. Las migraciones requieren una base de datos."
        )
    return url


def run_migrations_offline() -> None:
    """Genera SQL sin conectar a la base."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones contra la base conectada.

    transaction_per_migration=True: cada revision commitea por separado, de modo
    que un fallo en la revision N deja aplicadas 1..N-1 con alembic_version
    coherente y el proceso es reintentable.

    El lock de exclusion mutua entre tasks de ECS lo toma backend/db_bootstrap.py;
    no agregarlo aca tambien o las dos sesiones se bloquean entre si.
    """
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
