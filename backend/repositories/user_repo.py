"""Repositorio de usuarios (gestion por el super admin). Requiere base de datos."""

import logging

import psycopg2

from backend.db import get_db, is_db_available, load_query
from backend.error_handlers import ConflictError, DomainError

logger = logging.getLogger(__name__)

_COLUMNS = ("id", "username", "display_name", "role", "active", "created_at")


class UserRepository:
    """Acceso a la tabla users para el ABM de cuentas."""

    def _ensure_db(self) -> None:
        if not is_db_available():
            raise DomainError(
                "La gestion de usuarios requiere base de datos.",
                status_code=503,
                error_type="db_required",
            )

    def _queries(self):
        return load_query("users.sql")

    def list(self) -> list[dict]:
        """Lista todas las cuentas."""
        self._ensure_db()
        queries = self._queries()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["list_users"])
                rows = cur.fetchall()
        return [dict(zip(_COLUMNS, row)) for row in rows]

    def find_by_id(self, user_id: int) -> dict | None:
        """Busca una cuenta por id (incluye inactivas)."""
        self._ensure_db()
        queries = self._queries()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["find_user_by_id"], (user_id,))
                row = cur.fetchone()
        return dict(zip(_COLUMNS, row)) if row else None

    def create(
        self,
        username: str,
        password_hash: str,
        salt: str,
        display_name: str,
        role: str,
    ) -> dict:
        """Crea una cuenta nueva. Lanza ConflictError si el username ya existe."""
        self._ensure_db()
        queries = self._queries()
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        queries["insert_user"],
                        (username, password_hash, salt, display_name, role),
                    )
                    new_id = cur.fetchone()[0]
        except psycopg2.IntegrityError as exc:
            raise ConflictError(f"El usuario '{username}' ya existe.") from exc
        created = self.find_by_id(new_id)
        if created is None:
            raise DomainError("No se pudo crear el usuario.", status_code=500)
        return created

    def update_profile(self, user_id: int, display_name: str, role: str, active: bool) -> bool:
        """Actualiza display_name, rol y estado activo. Retorna False si no existe."""
        self._ensure_db()
        queries = self._queries()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["update_user_profile"], (display_name, role, active, user_id))
                return cur.fetchone() is not None

    def update_password(self, user_id: int, password_hash: str, salt: str) -> bool:
        """Reemplaza la password de una cuenta. Retorna False si no existe."""
        self._ensure_db()
        queries = self._queries()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(queries["update_user_password"], (password_hash, salt, user_id))
                return cur.fetchone() is not None
