import hashlib
import json
from datetime import datetime
from typing import Dict

from backend.models.ledger import Block, LedgerList, LedgerVerification
from backend.repositories.ledger_repo import LedgerRepository

GENESIS_PREV_HASH = "0" * 64


class LedgerService:
    """Blockchain simulada: cadena de bloques enlazados por hash SHA-256 en memoria."""

    def __init__(self, repo: LedgerRepository) -> None:
        self._repo = repo
        self._ensure_genesis()

    @staticmethod
    def _compute_hash(index: int, timestamp: str, tx_type: str, payload: Dict, prev_hash: str) -> str:
        contenido = {
            "index": index,
            "timestamp": timestamp,
            "tx_type": tx_type,
            "payload": payload,
            "prev_hash": prev_hash,
        }
        serializado = json.dumps(contenido, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(serializado.encode("utf-8")).hexdigest()

    def _ensure_genesis(self) -> None:
        if self._repo.is_empty():
            timestamp = datetime.now().isoformat()
            block_hash = self._compute_hash(0, timestamp, "genesis", {}, GENESIS_PREV_HASH)
            genesis = Block(
                index=0,
                timestamp=timestamp,
                tx_type="genesis",
                payload={},
                prev_hash=GENESIS_PREV_HASH,
                hash=block_hash,
            )
            self._repo.add(genesis)

    def append(self, tx_type: str, payload: Dict) -> Block:
        prev = self._repo.last()
        index = prev.index + 1
        timestamp = datetime.now().isoformat()
        block_hash = self._compute_hash(index, timestamp, tx_type, payload, prev.hash)
        block = Block(
            index=index,
            timestamp=timestamp,
            tx_type=tx_type,
            payload=payload,
            prev_hash=prev.hash,
            hash=block_hash,
        )
        return self._repo.add(block)

    def list_blocks(self) -> LedgerList:
        return LedgerList(blocks=self._repo.list_all())

    def verify_chain(self) -> LedgerVerification:
        blocks = self._repo.list_all()
        prev_hash = GENESIS_PREV_HASH
        for block in blocks:
            recalculado = self._compute_hash(
                block.index, block.timestamp, block.tx_type, block.payload, block.prev_hash
            )
            if recalculado != block.hash or block.prev_hash != prev_hash:
                return LedgerVerification(valido=False, total_bloques=len(blocks), roto_en=block.index)
            prev_hash = block.hash
        return LedgerVerification(valido=True, total_bloques=len(blocks), roto_en=None)
