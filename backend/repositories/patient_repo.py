from typing import List

from backend.models.patient import Patient


class PatientRepository:
    def __init__(self) -> None:
        self._store: List[Patient] = []
        self._next_id = 1

    def next_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def add(self, patient: Patient) -> Patient:
        self._store.append(patient)
        return patient

    def list_all(self) -> List[Patient]:
        return list(self._store)
