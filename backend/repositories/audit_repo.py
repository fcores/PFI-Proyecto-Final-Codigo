"""Repositorio de auditoria con soporte PostgreSQL y fallback en memoria."""

import logging
from datetime import datetime

from backend.models.audit import AuditCase, Correction, Dictamen

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repositorio de casos de auditoria, dictamenes y correcciones."""

    def __init__(self) -> None:
        """Inicializa los almacenes en memoria."""
        try:
            self._cases: list[AuditCase] = []
            self._dictamenes: list[Dictamen] = []
            self._corrections: list[Correction] = []
            self._next_case_id = 1
            self._next_dictamen_id = 1
            self._next_correction_id = 1
        except Exception as exc:
            logger.error("Error al inicializar AuditRepository: %s", exc, exc_info=True)
            raise

    def _db_available(self) -> bool:
        """Verifica si la base de datos esta disponible."""
        try:
            from backend.db import is_db_available

            return is_db_available()
        except Exception:
            return False

    def add_case(self, prescription_id: int, status: str, snapshot=None) -> AuditCase:
        """Crea un caso de auditoria para una prescripcion.

        snapshot opcional permite enriquecer el caso en modo memoria con
        datos clinicos y de validacion para el detalle de auditoria.
        """
        try:
            extra = snapshot or {}
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["insert_audit_case"], (prescription_id, status))
                        row = cur.fetchone()
                        case_id = row[0]
                case = AuditCase(
                    id=case_id,
                    prescription_id=prescription_id,
                    status=status,
                    assigned_auditor=None,
                    created_at=datetime.now(),
                    **extra,
                )
                return case
            case = AuditCase(
                id=self._next_case_id,
                prescription_id=prescription_id,
                status=status,
                assigned_auditor=None,
                created_at=datetime.now(),
                **extra,
            )
            self._next_case_id += 1
            self._cases.append(case)
            return case
        except Exception as exc:
            logger.error("Error al agregar caso de auditoria: %s", exc, exc_info=True)
            raise

    def list_pending(self) -> list[AuditCase]:
        """Lista los casos pendientes o en revision."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_pending_cases"])
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    result.append(AuditCase(**data))
                return result
            return [c for c in self._cases if c.status in ("pendiente", "en_revision")]
        except Exception as exc:
            logger.error("Error al listar casos pendientes: %s", exc, exc_info=True)
            raise

    def find_case_by_id(self, case_id: int) -> AuditCase | None:
        """Busca un caso de auditoria por su ID."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["find_audit_case_by_id"], (case_id,))
                        columns = [desc[0] for desc in cur.description]
                        row = cur.fetchone()
                if row is None:
                    return None
                data = dict(zip(columns, row))
                return AuditCase(**data)
            for case in self._cases:
                if case.id == case_id:
                    return case
            return None
        except Exception as exc:
            logger.error("Error al buscar caso de auditoria %s: %s", case_id, exc, exc_info=True)
            raise

    def claim_case(self, case_id: int, auditor: str) -> bool:
        """Intenta reservar un caso pendiente para un auditor (control de concurrencia).

        Returns True si el caso fue reservado, False si ya estaba tomado.
        """
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["claim_audit_case"], (auditor, case_id))
                        row = cur.fetchone()
                        return row is not None
            for case in self._cases:
                if case.id == case_id and case.status == "pendiente" and case.assigned_auditor is None:
                    case.status = "en_revision"
                    case.assigned_auditor = auditor
                    return True
            return False
        except Exception as exc:
            logger.error("Error al reservar caso %s: %s", case_id, exc, exc_info=True)
            raise

    def update_case_status(self, case_id: int, new_status: str, auditor: str) -> None:
        """Actualiza el estado y auditor asignado de un caso."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["update_audit_case_status"], (new_status, auditor, case_id))
                return
            for case in self._cases:
                if case.id == case_id:
                    case.status = new_status
                    case.assigned_auditor = auditor
                    break
        except Exception as exc:
            logger.error("Error al actualizar estado del caso %s: %s", case_id, exc, exc_info=True)
            raise

    def add_dictamen(
        self,
        case_id: int,
        resultado: str,
        justificacion: str,
        auditor_username: str,
        blockchain_tx_id: str,
    ) -> Dictamen:
        """Registra un dictamen para un caso de auditoria."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            queries["insert_dictamen"],
                            (case_id, resultado, justificacion, auditor_username, blockchain_tx_id),
                        )
                        row = cur.fetchone()
                        dictamen_id = row[0]
                dictamen = Dictamen(
                    id=dictamen_id,
                    audit_case_id=case_id,
                    resultado=resultado,
                    justificacion=justificacion,
                    auditor_username=auditor_username,
                    blockchain_tx_id=blockchain_tx_id,
                    created_at=datetime.now(),
                )
                return dictamen
            dictamen = Dictamen(
                id=self._next_dictamen_id,
                audit_case_id=case_id,
                resultado=resultado,
                justificacion=justificacion,
                auditor_username=auditor_username,
                blockchain_tx_id=blockchain_tx_id,
                created_at=datetime.now(),
            )
            self._next_dictamen_id += 1
            self._dictamenes.append(dictamen)
            return dictamen
        except Exception as exc:
            logger.error("Error al agregar dictamen para caso %s: %s", case_id, exc, exc_info=True)
            raise

    def find_dictamen_by_case(self, case_id: int) -> Dictamen | None:
        """Busca el dictamen mas reciente de un caso."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_dictamen_by_case"], (case_id,))
                        columns = [desc[0] for desc in cur.description]
                        row = cur.fetchone()
                if row is None:
                    return None
                data = dict(zip(columns, row))
                return Dictamen(**data)
            for d in reversed(self._dictamenes):
                if d.audit_case_id == case_id:
                    return d
            return None
        except Exception as exc:
            logger.error("Error al buscar dictamen del caso %s: %s", case_id, exc, exc_info=True)
            raise

    def add_correction(
        self,
        case_id: int,
        campo: str,
        valor_anterior: str,
        valor_nuevo: str,
        justificacion: str,
        auditor_username: str,
        blockchain_tx_id: str,
    ) -> Correction:
        """Registra una correccion de dato clinico."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        params = (
                            case_id,
                            campo,
                            valor_anterior,
                            valor_nuevo,
                            justificacion,
                            auditor_username,
                            blockchain_tx_id,
                        )
                        cur.execute(queries["insert_correction"], params)
                        row = cur.fetchone()
                        correction_id = row[0]
                correction = Correction(
                    id=correction_id,
                    audit_case_id=case_id,
                    campo=campo,
                    valor_anterior=valor_anterior,
                    valor_nuevo=valor_nuevo,
                    justificacion=justificacion,
                    auditor_username=auditor_username,
                    blockchain_tx_id=blockchain_tx_id,
                    created_at=datetime.now(),
                )
                return correction
            correction = Correction(
                id=self._next_correction_id,
                audit_case_id=case_id,
                campo=campo,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                justificacion=justificacion,
                auditor_username=auditor_username,
                blockchain_tx_id=blockchain_tx_id,
                created_at=datetime.now(),
            )
            self._next_correction_id += 1
            self._corrections.append(correction)
            return correction
        except Exception as exc:
            logger.error("Error al agregar correccion para caso %s: %s", case_id, exc, exc_info=True)
            raise

    def update_prescription_estado(self, prescription_id: int, new_estado: str) -> None:
        """Propaga el resultado del dictamen al estado de la prescripcion."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["update_prescription_estado"], (new_estado, prescription_id))
        except Exception as exc:
            logger.error(
                "Error al actualizar estado de prescripcion %s: %s", prescription_id, exc, exc_info=True,
            )
            raise

    def apply_correction_to_prescription(self, prescription_id: int, campo: str, valor_nuevo: str) -> None:
        """Aplica una correccion directamente al registro de la prescripcion."""
        from backend.models.audit import CAMPOS_CORREGIBLES

        if campo not in CAMPOS_CORREGIBLES:
            return
        try:
            if self._db_available():
                from backend.db import get_db

                with get_db() as conn:
                    with conn.cursor() as cur:
                        sql = "UPDATE prescriptions SET %s = %%s, updated_at = NOW() WHERE id = %%s" % campo
                        cur.execute(sql, (valor_nuevo, prescription_id))
        except Exception as exc:
            logger.error(
                "Error al aplicar correccion campo=%s a prescripcion %s: %s",
                campo, prescription_id, exc, exc_info=True,
            )
            raise

    def list_corrections_by_case(self, case_id: int) -> list[Correction]:
        """Lista las correcciones de un caso ordenadas por fecha."""
        try:
            if self._db_available():
                from backend.db import get_db, load_query

                queries = load_query("audit.sql")
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(queries["select_corrections_by_case"], (case_id,))
                        columns = [desc[0] for desc in cur.description]
                        rows = cur.fetchall()
                result = []
                for row in rows:
                    data = dict(zip(columns, row))
                    result.append(Correction(**data))
                return result
            return [c for c in self._corrections if c.audit_case_id == case_id]
        except Exception as exc:
            logger.error("Error al listar correcciones del caso %s: %s", case_id, exc, exc_info=True)
            raise
