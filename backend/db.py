"""
Modulo de acceso a base de datos PostgreSQL.
Provee pool de conexiones, context manager y utilidades de carga de queries.
Si DATABASE_URL no esta configurada, el sistema opera en modo in-memory.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = logging.getLogger(__name__)
_handler = RotatingFileHandler("db.log", maxBytes=5_000_000, backupCount=3)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

_pool = None
_use_db = False
_pool_initialized = False


def _init_pool():
    """Crea el pool de conexiones si DATABASE_URL esta definida."""
    global _pool, _use_db, _pool_initialized
    try:
        if _pool_initialized:
            return
        _pool_initialized = True
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.info("DATABASE_URL no configurada, operando en modo in-memory")
            _use_db = False
            return
        from psycopg2.pool import SimpleConnectionPool
        _pool = SimpleConnectionPool(minconn=1, maxconn=10, dsn=database_url)
        _use_db = True
        logger.info("Pool de conexiones PostgreSQL creado exitosamente")
    except Exception as exc:
        logger.error("Error al crear pool de conexiones: %s", exc, exc_info=True)
        _use_db = False
        _pool = None


def get_connection_pool():
    """Retorna el pool de conexiones singleton, creandolo si no existe."""
    try:
        if not _pool_initialized:
            _init_pool()
        return _pool
    except Exception as exc:
        logger.error("Error al obtener connection pool: %s", exc, exc_info=True)
        raise


def is_db_available():
    """Retorna True si la base de datos esta disponible y el pool fue creado."""
    try:
        if not _pool_initialized:
            _init_pool()
        return _use_db and _pool is not None
    except Exception as exc:
        logger.error("Error al verificar disponibilidad de DB: %s", exc, exc_info=True)
        return False


class get_db:
    """Context manager que provee una conexion del pool, commit en exito, rollback en error."""

    def __init__(self):
        """Inicializa el context manager de conexion."""
        try:
            self._conn = None
            self._pool = None
        except Exception as exc:
            logger.error("Error al inicializar get_db: %s", exc, exc_info=True)
            raise

    def __enter__(self):
        """Obtiene una conexion del pool."""
        try:
            self._pool = get_connection_pool()
            if self._pool is None:
                raise RuntimeError("Pool de conexiones no disponible")
            self._conn = self._pool.getconn()
            return self._conn
        except Exception as exc:
            logger.error("Error al obtener conexion del pool: %s", exc, exc_info=True)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit en exito, rollback en error, y devuelve la conexion al pool."""
        try:
            if self._conn is not None:
                if exc_type is None:
                    self._conn.commit()
                else:
                    self._conn.rollback()
                self._pool.putconn(self._conn)
            return False
        except Exception as exc:
            logger.error("Error en get_db __exit__: %s", exc, exc_info=True)
            return False


def init_db():
    """Lee y ejecuta sql/schema.sql para crear las tablas si no existen."""
    try:
        if not is_db_available():
            logger.info("Base de datos no disponible, omitiendo inicializacion de schema")
            return
        schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
        with open(str(schema_path), "r", encoding="utf-8") as f:
            schema_sql = f.read()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
        logger.info("Schema de base de datos inicializado correctamente")
    except Exception as exc:
        logger.error("Error al inicializar schema de DB: %s", exc, exc_info=True)


def load_query(filename):
    """Lee un archivo .sql y retorna un dict con las queries nombradas.

    Parsea comentarios con formato '-- name: nombre_query' como delimitadores.
    """
    try:
        sql_path = Path(__file__).resolve().parent.parent / "sql" / filename
        with open(str(sql_path), "r", encoding="utf-8") as f:
            content = f.read()
        queries = {}
        current_name = None
        current_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("-- name:"):
                if current_name and current_lines:
                    queries[current_name] = "\n".join(current_lines).strip()
                current_name = stripped.replace("-- name:", "").strip()
                current_lines = []
            else:
                if current_name is not None:
                    current_lines.append(line)
        if current_name and current_lines:
            queries[current_name] = "\n".join(current_lines).strip()
        return queries
    except Exception as exc:
        logger.error("Error al cargar query desde %s: %s", filename, exc, exc_info=True)
        raise
