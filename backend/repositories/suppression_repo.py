"""Repositorio de solicitudes de supresion de datos de pacientes (RF-38).

Con DATABASE_URL usa patient_suppression_requests; sin ella opera en memoria.
"""

# Annotations diferidas: la clase define un metodo `list` que ensombrece al
# builtin dentro del cuerpo de la clase.
from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.db import get_db, is_db_available, load_query

logger = logging.getLogger(__name__)

_COLUMNS = (
    "id",
    "patient_id",
    "requested_by",
    "motivo",
    "requested_at",
    "ejecutable_desde",
    "executed_at",
    "estado",
)


class SuppressionRepository:
    """Acceso a la tabla patient_suppression_requests."""

    def __init__(self) -> None:
        """Inicializa el almacenamiento en memoria para el modo sin base."""
        try:
            self._store: list[dict] = []
        except Exception as exc:
            logger.error("Error al inicializar SuppressionRepository: %s", exc, exc_info=True)
            raise

    def _ejecutar(self, nombre: str, parametros: tuple, muchas: bool = False):
        """Ejecuta una consulta nombrada de suppression.sql y devuelve filas como dict."""
        try:
            queries = load_query("suppression.sql")
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(queries[nombre], parametros)
                    if muchas:
                        filas = cur.fetchall()
                        resultado = []
                        for fila in filas:
                            resultado.append(dict(zip(_COLUMNS, fila)))
                        return resultado
                    fila = cur.fetchone()
                    if fila is None:
                        return None
                    return dict(zip(_COLUMNS, fila))
        except Exception as exc:
            logger.error("Error al ejecutar %s: %s", nombre, exc, exc_info=True)
            raise

    def insert(self, patient_id: int, requested_by: str, motivo: str | None, ejecutable_desde: datetime) -> dict:
        """Registra una solicitud de supresion pendiente."""
        try:
            if is_db_available():
                return self._ejecutar("insert_request", (patient_id, requested_by, motivo, ejecutable_desde))
            fila = {
                "id": len(self._store) + 1,
                "patient_id": patient_id,
                "requested_by": requested_by,
                "motivo": motivo,
                "requested_at": datetime.now(UTC).replace(tzinfo=None),
                "ejecutable_desde": ejecutable_desde,
                "executed_at": None,
                "estado": "pendiente",
            }
            self._store.append(fila)
            return dict(fila)
        except Exception as exc:
            logger.error("Error al registrar la solicitud de supresion: %s", exc, exc_info=True)
            raise

    def list(self) -> list[dict]:
        """Lista todas las solicitudes, de la mas reciente a la mas antigua."""
        try:
            if is_db_available():
                return self._ejecutar("list_requests", (), muchas=True)
            resultado = []
            for fila in reversed(self._store):
                resultado.append(dict(fila))
            return resultado
        except Exception as exc:
            logger.error("Error al listar las solicitudes de supresion: %s", exc, exc_info=True)
            raise

    def list_due(self, ahora: datetime) -> list[dict]:
        """Lista las solicitudes pendientes cuyo periodo de retencion ya vencio."""
        try:
            if is_db_available():
                return self._ejecutar("list_due_requests", (ahora,), muchas=True)
            resultado = []
            for fila in self._store:
                if fila["estado"] == "pendiente" and fila["ejecutable_desde"] <= ahora:
                    resultado.append(dict(fila))
            return resultado
        except Exception as exc:
            logger.error("Error al listar las solicitudes vencidas: %s", exc, exc_info=True)
            raise

    def find_pending(self, patient_id: int) -> dict | None:
        """Devuelve la solicitud pendiente del paciente, si existe."""
        try:
            if is_db_available():
                return self._ejecutar("find_pending_by_patient", (patient_id,))
            for fila in self._store:
                if fila["patient_id"] == patient_id and fila["estado"] == "pendiente":
                    return dict(fila)
            return None
        except Exception as exc:
            logger.error("Error al buscar la solicitud del paciente %s: %s", patient_id, exc, exc_info=True)
            raise

    def mark_executed(self, request_id: int) -> dict | None:
        """Marca una solicitud como ejecutada."""
        try:
            if is_db_available():
                return self._ejecutar("mark_executed", (request_id,))
            for fila in self._store:
                if fila["id"] == request_id:
                    fila["estado"] = "ejecutada"
                    fila["executed_at"] = datetime.now(UTC).replace(tzinfo=None)
                    return dict(fila)
            return None
        except Exception as exc:
            logger.error("Error al marcar la solicitud %s: %s", request_id, exc, exc_info=True)
            raise
