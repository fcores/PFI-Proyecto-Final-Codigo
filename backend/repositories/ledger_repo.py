from typing import List

from backend.models.ledger import Block


class LedgerRepository:
    def __init__(self) -> None:
        self._chain: List[Block] = []

    def add(self, block: Block) -> Block:
        self._chain.append(block)
        return block

    def last(self) -> Block:
        return self._chain[-1]

    def is_empty(self) -> bool:
        return len(self._chain) == 0

    def list_all(self) -> List[Block]:
        return list(self._chain)
