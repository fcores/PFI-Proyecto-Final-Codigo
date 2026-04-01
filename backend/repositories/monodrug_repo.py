from typing import List

from backend.models.monodrug import Monodrug


class MonodrugRepository:
    def __init__(self) -> None:
        self._store: List[Monodrug] = []
        self._next_id = 1

    def next_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def add(self, monodrug: Monodrug) -> Monodrug:
        self._store.append(monodrug)
        return monodrug

    def list_all(self) -> List[Monodrug]:
        return list(self._store)

    def find_by_sap_id(self, sap_id: str) -> Monodrug | None:
        return next((item for item in self._store if item.sap_id == sap_id), None)
