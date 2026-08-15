"""
Vacia las tablas de datos de la base PostgreSQL preservando la estructura.

Ejecuta un unico TRUNCATE ... RESTART IDENTITY CASCADE sobre todas las tablas
del schema public, salvo las listadas en TABLAS_PRESERVADAS.

La conexion sale de DATABASE_URL via backend.config.get_settings(), que resuelve
el archivo .env relativo al directorio de trabajo: correr desde la raiz del repo.

Uso:
    python scripts/vaciar_db.py            # pide confirmacion interactiva
    python scripts/vaciar_db.py --yes      # sin confirmacion (scripts/CI)

Codigos de salida: 0 exito, 1 error de configuracion o conexion, 2 cancelado.
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psycopg2 import sql  # noqa: E402

from backend.config import get_settings  # noqa: E402
from backend.db import get_db, is_db_available  # noqa: E402

# Tablas que el script nunca toca. 'users' conserva las cuentas existentes;
# 'alembic_version' mantiene el schema marcado en head para que
# backend/db_bootstrap.py no reintente las migraciones en el proximo arranque.
TABLAS_PRESERVADAS = frozenset({"users", "alembic_version"})

# Secuencias standalone (no OWNED BY ninguna columna), por lo que RESTART IDENTITY
# no las alcanza y hay que reiniciarlas explicitamente. prescription_id_seq genera
# el prescription_code en backend/repositories/prescription_repo.py.
SECUENCIAS_STANDALONE = ("prescription_id_seq",)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CANCELADO = 2


def describir_conexion(database_url):
    """Retorna (host, nombre_base) de la URL, sin exponer credenciales."""
    partes = urlsplit(database_url)
    host = partes.hostname or "desconocido"
    if partes.port:
        host = "%s:%s" % (host, partes.port)
    nombre_base = partes.path.lstrip("/") or "desconocida"
    return host, nombre_base


def descubrir_tablas(cur):
    """Retorna las tablas de public a vaciar, excluyendo las preservadas."""
    cur.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
          AND table_name <> ALL(%s)
        ORDER BY table_name
        """,
        (list(TABLAS_PRESERVADAS),),
    )
    return [fila[0] for fila in cur.fetchall()]


def contar_filas(cur, tabla):
    """Retorna la cantidad de filas de una tabla del schema public."""
    cur.execute(
        sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier("public", tabla))
    )
    return cur.fetchone()[0]


def contar_tabla_opcional(cur, tabla):
    """Igual que contar_filas pero retorna None si la tabla no existe."""
    cur.execute("SELECT to_regclass(%s)", ("public." + tabla,))
    if cur.fetchone()[0] is None:
        return None
    return contar_filas(cur, tabla)


def obtener_version_alembic(cur):
    """Retorna la version actual de alembic, o None si la tabla no existe."""
    cur.execute("SELECT to_regclass('public.alembic_version')")
    if cur.fetchone()[0] is None:
        return None
    cur.execute("SELECT version_num FROM alembic_version")
    fila = cur.fetchone()
    return fila[0] if fila else None


def confirmar(host, nombre_base, conteos, filas_users):
    """Pide al usuario escribir el nombre de la base. True si confirma."""
    total = sum(conteos.values())
    print("")
    print("Se van a VACIAR las siguientes tablas:")
    print("  Servidor: %s" % host)
    print("  Base:     %s" % nombre_base)
    print("")
    ancho = max(len(t) for t in conteos)
    for tabla, filas in sorted(conteos.items()):
        print("    %-*s  %8d filas" % (ancho, tabla, filas))
    print("    %-*s  %8d filas en total" % (ancho, "", total))
    print("")
    preservadas = "users (%d filas, intacta), alembic_version" % (
        filas_users if filas_users is not None else 0
    )
    print("  Se preservan: %s" % preservadas)
    print("")
    respuesta = input(
        "Escribi el nombre de la base ('%s') para confirmar: " % nombre_base
    ).strip()
    return respuesta == nombre_base


def vaciar(cur, tablas):
    """Ejecuta el TRUNCATE de todas las tablas en una unica sentencia.

    Una sola sentencia evita tener que ordenar por dependencias de clave foranea.
    """
    objetivo = sql.SQL(", ").join(sql.Identifier("public", t) for t in tablas)
    cur.execute(
        sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(objetivo)
    )


def reiniciar_secuencias(cur):
    """Reinicia las secuencias standalone que existan. Retorna las reiniciadas."""
    reiniciadas = []
    for secuencia in SECUENCIAS_STANDALONE:
        cur.execute("SELECT to_regclass(%s)", ("public." + secuencia,))
        if cur.fetchone()[0] is None:
            continue
        cur.execute(
            sql.SQL("ALTER SEQUENCE {} RESTART").format(
                sql.Identifier("public", secuencia)
            )
        )
        reiniciadas.append(secuencia)
    return reiniciadas


def main():
    parser = argparse.ArgumentParser(
        description="Vacia las tablas de datos de PostgreSQL preservando el schema."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="omite la confirmacion interactiva",
    )
    args = parser.parse_args()

    database_url = get_settings().database_url
    if not database_url:
        print(
            "ERROR: DATABASE_URL no esta configurada.\n"
            "  Agregala al archivo .env, por ejemplo:\n"
            "    DATABASE_URL=postgresql://usuario:password@host:5432/medchain\n"
            "  Y ejecuta este script desde la raiz del repositorio "
            "(el .env se resuelve relativo al directorio actual).",
            file=sys.stderr,
        )
        return EXIT_ERROR

    host, nombre_base = describir_conexion(database_url)

    if not is_db_available():
        print(
            "ERROR: no se pudo conectar a la base en %s.\n"
            "  Revisa DATABASE_URL, la conectividad de red y las credenciales."
            % host,
            file=sys.stderr,
        )
        return EXIT_ERROR

    with get_db() as conn:
        with conn.cursor() as cur:
            tablas = descubrir_tablas(cur)
            if not tablas:
                print("No hay tablas para vaciar en el schema public.")
                return EXIT_OK

            conteos = {tabla: contar_filas(cur, tabla) for tabla in tablas}
            users_antes = contar_tabla_opcional(cur, "users")

        # Cierra la transaccion de lectura para no quedar idle-in-transaction
        # mientras el script espera la respuesta del usuario.
        conn.commit()

        if not args.yes:
            if not confirmar(host, nombre_base, conteos, users_antes):
                print("Cancelado: no se modifico nada.")
                return EXIT_CANCELADO

        with conn.cursor() as cur:
            vaciar(cur, tablas)
            secuencias = reiniciar_secuencias(cur)

            # Red de seguridad: si un CASCADE llegara a alcanzar users, la
            # excepcion propaga y get_db() hace rollback de todo.
            users_despues = contar_tabla_opcional(cur, "users")
            if users_despues != users_antes:
                raise RuntimeError(
                    "La tabla users cambio de %s a %s filas durante el vaciado; "
                    "se revierte la operacion completa."
                    % (users_antes, users_despues)
                )

            version_alembic = obtener_version_alembic(cur)

    print("")
    print("Vaciado completo en %s / %s" % (host, nombre_base))
    ancho = max(len(t) for t in conteos)
    for tabla, filas in sorted(conteos.items()):
        print("    %-*s  %8d filas borradas" % (ancho, tabla, filas))
    print("    %-*s  %8d filas borradas en total" % (ancho, "", sum(conteos.values())))
    print("")
    if secuencias:
        print("  Secuencias reiniciadas: %s" % ", ".join(secuencias))
    print(
        "  Preservado: users (%s filas), alembic_version (%s)"
        % (
            users_despues if users_despues is not None else "tabla ausente",
            version_alembic or "sin version",
        )
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
