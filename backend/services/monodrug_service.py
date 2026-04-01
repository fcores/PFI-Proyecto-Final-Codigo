from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.monodrug import Monodrug, MonodrugList
from backend.repositories.monodrug_repo import MonodrugRepository
from backend.services.excel_import_service import ExcelImportService


class MonodrugService:
    IMPORT_ALIASES = {
        "descripcion": ["descripcion", "descripción"],
        "sap_id": ["sap_id", "id sap", "idsap"],
    }

    def __init__(self, repo: MonodrugRepository, excel_importer: ExcelImportService) -> None:
        self._repo = repo
        self._excel_importer = excel_importer

    def create(self, *, descripcion: str, sap_id: str) -> Monodrug:
        monodrug = Monodrug(
            id=self._repo.next_id(),
            descripcion=descripcion,
            sap_id=sap_id,
        )
        return self._repo.add(monodrug)

    def list_all(self) -> MonodrugList:
        return MonodrugList(monodrugs=self._repo.list_all())

    def find_by_sap_id(self, sap_id: str) -> Monodrug | None:
        return self._repo.find_by_sap_id(sap_id)

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
        errors: list[BulkImportError] = []
        imported_count = 0

        for index, row in enumerate(rows, start=2):
            try:
                self.create(
                    descripcion=self._excel_importer.as_required_str(row, "descripcion", "descripción"),
                    sap_id=self._excel_importer.as_required_str(row, "sap_id", "id sap"),
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
