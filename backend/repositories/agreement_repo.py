from typing import List

from backend.models.agreement import Agreement


class AgreementRepository:
    def __init__(self) -> None:
        self._store: List[Agreement] = []
        self._next_id = 1

    def next_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def add(self, agreement: Agreement) -> Agreement:
        self._store.append(agreement)
        return agreement

    def list_all(self) -> List[Agreement]:
        return list(self._store)
