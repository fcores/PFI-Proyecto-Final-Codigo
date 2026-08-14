"""
Filtro de logging que redacta informacion de salud protegida (PHI) antes de
emitirla a cualquier handler. Previene filtraciones accidentales de datos
personales/clinicos en logs, excepciones y telemetria.
"""
import logging
import re
from typing import List, Pattern


_PHI_PATTERNS: List[Pattern] = [
    re.compile(
        r"\b(first_name|last_name|nombre|apellido|patient_name)"
        r"\s*[=:]\s*['\"]?[A-Za-zÀ-ÿ\s]{2,}['\"]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(birth_date|fecha_nacimiento)\s*[=:]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(credential_id|dni|documento)\s*[=:]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(diagnostico|treatment|tratamiento)\s*[=:]\s*['\"]?[^,;}{)]{3,}['\"]?",
        re.IGNORECASE,
    ),
]

_REDACTED = "[PHI_REDACTED]"


class PHIRedactionFilter(logging.Filter):
    """Reemplaza coincidencias de PHI con un placeholder en cada LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg and isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _redact(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def _redact(text: str) -> str:
    """Aplica los patrones de redaccion sobre un texto."""
    for pattern in _PHI_PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text


def install_phi_filter(logger_name: str = "") -> None:
    """Instala el filtro de redaccion en el logger indicado (root por defecto)."""
    target = logging.getLogger(logger_name)
    target.addFilter(PHIRedactionFilter())
