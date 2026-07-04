from typing import List

from backend.models.prescription import Prescription


class PrescriptionRepository:
    def __init__(self) -> None:
        self._store: List[Prescription] = []
        self._next_id = 1

    def next_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def add(self, prescription: Prescription) -> Prescription:
        self._store.append(prescription)
        return prescription

    def list_all(self) -> List[Prescription]:
        return list(self._store)
