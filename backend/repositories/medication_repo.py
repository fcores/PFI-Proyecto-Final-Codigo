from typing import List

from backend.models.medication import Medication


class MedicationRepository:
    def __init__(self) -> None:
        self._store: List[Medication] = []
        self._next_id = 1

    def next_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def add(self, medication: Medication) -> Medication:
        self._store.append(medication)
        return medication

    def list_all(self) -> List[Medication]:
        return list(self._store)
