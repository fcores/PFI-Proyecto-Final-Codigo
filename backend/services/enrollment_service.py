from datetime import datetime
from typing import List

from fastapi import HTTPException

from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.enrollment import Enrollment, EnrollmentList
from backend.repositories.enrollment_repo import EnrollmentRepository
from backend.services.excel_import_service import ExcelImportService


class EnrollmentService:
    IMPORT_ALIASES = {
        "diagnostico": ["diagnostico", "diagnóstico"],
        "medications": ["medications", "medicamentos", "medicamento"],
    }

    def __init__(self, repo: EnrollmentRepository, excel_importer: ExcelImportService) -> None:
        self._repo = repo
        self._excel_importer = excel_importer

    def _validate_type(self, tipo: str) -> None:
        if not self._repo.is_valid_type(tipo):
            raise HTTPException(status_code=404, detail=f"Tipo '{tipo}' no reconocido.")

    @staticmethod
    def _build_code(tipo: str, seq: int) -> str:
        tipo_letra = tipo.split("-")[1].upper()
        return f"EMP-{tipo_letra}-{seq:04d}"

    def create(
        self,
        *,
        tipo: str,
        medications: List[str],
        diagnostico: str,
    ) -> Enrollment:
        self._validate_type(tipo)
        seq = self._repo.next_id(tipo)
        enrollment = Enrollment(
            id=seq,
            enrollment_code=self._build_code(tipo, seq),
            tipo=tipo,
            medications=medications,
            diagnostico=diagnostico,
            created_at=datetime.now(),
        )
        return self._repo.add(tipo, enrollment)

    def list_by_type(self, tipo: str) -> EnrollmentList:
        self._validate_type(tipo)
        return EnrollmentList(enrollments=self._repo.list_by_type(tipo))

    def bulk_import(self, tipo: str, file_bytes: bytes, filename: str) -> BulkImportResult:
        self._validate_type(tipo)
        rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
        errors: list[BulkImportError] = []
        imported_count = 0

        for index, row in enumerate(rows, start=2):
            try:
                self.create(
                    tipo=tipo,
                    diagnostico=self._excel_importer.as_required_str(row, "diagnostico", "diagnóstico"),
                    medications=self._excel_importer.as_required_list(row, "medications", "medicamentos"),
                )
                imported_count += 1
            except Exception as exc:  # pragma: no cover - validation aggregation
                errors.append(BulkImportError(row_number=index, message=str(exc)))

        return BulkImportResult(
            total_rows=len(rows),
            imported_count=imported_count,
            failed_count=len(errors),
            errors=errors,
        )
