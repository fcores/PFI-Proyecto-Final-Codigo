"""Repositorio de claves de firma electronica de los prescriptores.

Con DATABASE_URL usa la tabla user_signing_keys; sin ella (local/test) opera
en memoria, igual que el resto de los repositorios.
"""

import logging
from datetime import UTC, datetime

from backend.db import get_db, is_db_available, load_query

logger = logging.getLogger(__name__)

_COLUMNS = (
    "id",
    "username",
    "algoritmo",
    "public_key_pem",
    "private_key_enc",
    "key_fingerprint",
    "created_at",
    "revoked_at",
)


class SigningKeyRepository:
    """Acceso a la tabla user_signing_keys."""

    def __init__(self) -> None:
        """Inicializa el almacenamiento en memoria para el modo sin base."""
        try:
            self._store: list[dict] = []
        except Exception as exc:
            logger.error("Error al inicializar SigningKeyRepository: %s", exc, exc_info=True)
            raise

    def _fila_a_dict(self, row) -> dict | None:
        """Convierte una fila de la consulta en diccionario."""
        try:
            if row is None:
                return None
            return dict(zip(_COLUMNS, row))
        except Exception as exc:
            logger.error("Error al convertir la fila de clave: %s", exc, exc_info=True)
            raise

    def find_active(self, username: str) -> dict | None:
        """Devuelve la clave vigente del usuario o None."""
        try:
            if not is_db_available():
                vigente = None
                for clave in self._store:
                    if clave["username"] == username and clave["revoked_at"] is None:
                        vigente = clave
                return vigente
            queries = load_query("signing_keys.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["find_active_key"], (username,))
                    return self._fila_a_dict(cur.fetchone())
        except Exception as exc:
            logger.error("Error al buscar la clave de firma de %s: %s", username, exc, exc_info=True)
            raise

    def find_by_fingerprint(self, fingerprint: str) -> dict | None:
        """Devuelve la clave registrada con esa huella (vigente o revocada)."""
        try:
            if not is_db_available():
                for clave in self._store:
                    if clave["key_fingerprint"] == fingerprint:
                        return clave
                return None
            queries = load_query("signing_keys.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["find_key_by_fingerprint"], (fingerprint,))
                    return self._fila_a_dict(cur.fetchone())
        except Exception as exc:
            logger.error("Error al buscar la clave por huella: %s", exc, exc_info=True)
            raise

    def insert(self, username: str, algoritmo: str, public_pem: str, private_enc: str, fingerprint: str) -> None:
        """Registra una clave nueva para el usuario."""
        try:
            if not is_db_available():
                self._store.append(
                    {
                        "id": len(self._store) + 1,
                        "username": username,
                        "algoritmo": algoritmo,
                        "public_key_pem": public_pem,
                        "private_key_enc": private_enc,
                        "key_fingerprint": fingerprint,
                        "created_at": datetime.now(UTC),
                        "revoked_at": None,
                    }
                )
                return
            queries = load_query("signing_keys.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["insert_key"], (username, algoritmo, public_pem, private_enc, fingerprint))
        except Exception as exc:
            logger.error("Error al registrar la clave de firma de %s: %s", username, exc, exc_info=True)
            raise

    def revoke(self, username: str) -> None:
        """Revoca todas las claves vigentes del usuario."""
        try:
            if not is_db_available():
                for clave in self._store:
                    if clave["username"] == username and clave["revoked_at"] is None:
                        clave["revoked_at"] = datetime.now(UTC)
                return
            queries = load_query("signing_keys.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries["revoke_keys"], (username,))
        except Exception as exc:
            logger.error("Error al revocar las claves de %s: %s", username, exc, exc_info=True)
            raise
