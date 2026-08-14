from pydantic import BaseModel, Field


class Block(BaseModel):
    index: int = Field(..., title="Índice del bloque")
    timestamp: str = Field(..., title="Marca de tiempo")
    tx_type: str = Field(..., title="Tipo de transacción")
    payload: dict = Field(default_factory=dict, title="Contenido de la transacción")
    prev_hash: str = Field(..., title="Hash del bloque anterior")
    hash: str = Field(..., title="Hash del bloque")


class LedgerList(BaseModel):
    blocks: list[Block]


class LedgerVerification(BaseModel):
    valido: bool = Field(..., title="Cadena íntegra")
    total_bloques: int = Field(..., title="Total de bloques")
    roto_en: int | None = Field(None, title="Índice del primer bloque inválido")
