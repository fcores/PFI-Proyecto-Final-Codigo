from datetime import date
from typing import Optional

from fastapi import UploadFile

from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.agreement import Agreement, AgreementList
from backend.repositories.agreement_repo import AgreementRepository
from backend.services.excel_import_service import ExcelImportService


class AgreementService:
    IMPORT_ALIASES = {
        "laboratorio": ["laboratorio"],
        "prestador": ["prestador"],
        "medicamento": ["medicamento"],
        "medicamento_sap": ["medicamento sap", "medicamento_sap"],
        "medico_auditor": ["medico auditor", "medico_auditor"],
        "fecha_inicial": ["fecha inicial", "fecha_inicial"],
        "fecha_final": ["fecha final", "fecha_final"],
        "condicion_recupero": ["condicion recupero", "condición recupero", "condicion de recupero"],
    }

    def __init__(self, repo: AgreementRepository, excel_importer: ExcelImportService) -> None:
        self._repo = repo
        self._excel_importer = excel_importer

    def create(
        self,
        *,
        laboratorio: str,
        prestador: str,
        medicamento: str,
        medicamento_sap: str,
        medico_auditor: Optional[str],
        fecha_inicial: date,
        fecha_final: date,
        condicion_recupero: str,
        contrato_file: Optional[UploadFile],
    ) -> Agreement:
        agreement = Agreement(
            id=self._repo.next_id(),
            laboratorio=laboratorio,
            prestador=prestador,
            medicamento=medicamento,
            medicamento_sap=medicamento_sap,
            medico_auditor=medico_auditor,
            fecha_inicial=fecha_inicial,
            fecha_final=fecha_final,
            condicion_recupero=condicion_recupero,
            contrato_filename=contrato_file.filename if contrato_file else None,
        )
        return self._repo.add(agreement)

    def list_all(self) -> AgreementList:
        return AgreementList(agreements=self._repo.list_all())

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
        errors: list[BulkImportError] = []
        imported_count = 0

        for index, row in enumerate(rows, start=2):
            try:
                self.create(
                    laboratorio=self._excel_importer.as_required_str(row, "laboratorio"),
                    prestador=self._excel_importer.as_required_str(row, "prestador"),
                    medicamento=self._excel_importer.as_required_str(row, "medicamento"),
                    medicamento_sap=self._excel_importer.as_required_str(
                        row,
                        "medicamento_sap",
                        "medicamento sap",
                    ),
                    medico_auditor=self._excel_importer.as_optional_str(row, "medico_auditor"),
                    fecha_inicial=self._excel_importer.as_required_date(
                        row,
                        "fecha_inicial",
                        "fecha inicial",
                    ),
                    fecha_final=self._excel_importer.as_required_date(
                        row,
                        "fecha_final",
                        "fecha final",
                    ),
                    condicion_recupero=self._excel_importer.as_required_str(
                        row,
                        "condicion_recupero",
                        "condición de recupero",
                    ),
                    contrato_file=None,
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
