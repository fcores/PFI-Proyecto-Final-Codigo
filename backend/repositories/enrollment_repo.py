from typing import Dict, List

from backend.models.enrollment import Enrollment

VALID_TYPES = frozenset({"tipo-a", "tipo-b"})


class EnrollmentRepository:
    def __init__(self) -> None:
        self._store: Dict[str, List[Enrollment]] = {t: [] for t in VALID_TYPES}
        self._counters: Dict[str, int] = {t: 1 for t in VALID_TYPES}

    def next_id(self, tipo: str) -> int:
        current = self._counters[tipo]
        self._counters[tipo] += 1
        return current

    def add(self, tipo: str, enrollment: Enrollment) -> Enrollment:
        self._store[tipo].append(enrollment)
        return enrollment

    def list_by_type(self, tipo: str) -> List[Enrollment]:
        return list(self._store[tipo])

    @staticmethod
    def is_valid_type(tipo: str) -> bool:
        return tipo in VALID_TYPES
