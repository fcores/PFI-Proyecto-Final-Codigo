from pydantic import BaseModel, Field


class BulkImportError(BaseModel):
    row_number: int = Field(..., title="Fila")
    message: str = Field(..., title="Error")


class BulkImportResult(BaseModel):
    total_rows: int = Field(..., title="Total de filas")
    imported_count: int = Field(..., title="Registros importados")
    failed_count: int = Field(..., title="Registros fallidos")
    errors: list[BulkImportError] = Field(default_factory=list, title="Errores")
