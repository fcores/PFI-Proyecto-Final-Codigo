from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.medication import Medication, MedicationList
from backend.repositories.medication_repo import MedicationRepository
from backend.repositories.monodrug_repo import MonodrugRepository
from backend.services.excel_import_service import ExcelImportService


class MedicationService:
    IMPORT_ALIASES = {
        "descripcion": ["descripcion", "descripción"],
        "ean": ["ean"],
        "codigo_alfabeta": ["codigo alfabeta", "código alfabeta", "codigo_alfabeta"],
        "tipo_conservacion": ["tipo conservacion", "tipo de conservacion", "tipo_conservacion"],
        "sap_id": ["sap_id", "id sap"],
        "monodroga_id": ["monodroga_id", "id monodroga", "id de monodroga"],
        "tamano_dimension": ["tamano dimension", "tamaño dimension", "tamano_dimension", "tamaño/dimension"],
    }

    def __init__(
        self,
        repo: MedicationRepository,
        monodrug_repo: MonodrugRepository,
        excel_importer: ExcelImportService,
    ) -> None:
        self._repo = repo
        self._monodrug_repo = monodrug_repo
        self._excel_importer = excel_importer

    def _resolve_monodrug_description(self, monodroga_id: str) -> str | None:
        monodrug = self._monodrug_repo.find_by_sap_id(monodroga_id)
        return monodrug.descripcion if monodrug else None

    def create(
        self,
        *,
        descripcion: str,
        ean: str,
        codigo_alfabeta: str,
        tipo_conservacion: str,
        sap_id: str,
        monodroga_id: str,
        tamano_dimension: str,
    ) -> Medication:
        medication = Medication(
            id=self._repo.next_id(),
            descripcion=descripcion,
            ean=ean,
            codigo_alfabeta=codigo_alfabeta,
            tipo_conservacion=tipo_conservacion,
            sap_id=sap_id,
            monodroga_id=monodroga_id,
            tamano_dimension=tamano_dimension,
            monodroga_descripcion=self._resolve_monodrug_description(monodroga_id),
        )
        return self._repo.add(medication)

    def list_all(self) -> MedicationList:
        medications = [
            medication.model_copy(
                update={
                    "monodroga_descripcion": self._resolve_monodrug_description(
                        medication.monodroga_id,
                    ),
                },
            )
            for medication in self._repo.list_all()
        ]
        return MedicationList(medications=medications)

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
        errors: list[BulkImportError] = []
        imported_count = 0

        for index, row in enumerate(rows, start=2):
            try:
                self.create(
                    descripcion=self._excel_importer.as_required_str(row, "descripcion", "descripción"),
                    ean=self._excel_importer.as_required_str(row, "ean"),
                    codigo_alfabeta=self._excel_importer.as_required_str(
                        row,
                        "codigo_alfabeta",
                        "código alfabeta",
                    ),
                    tipo_conservacion=self._excel_importer.as_required_str(
                        row,
                        "tipo_conservacion",
                        "tipo de conservación",
                    ),
                    sap_id=self._excel_importer.as_required_str(row, "sap_id", "id sap"),
                    monodroga_id=self._excel_importer.as_required_str(
                        row,
                        "monodroga_id",
                        "id de monodroga",
                    ),
                    tamano_dimension=self._excel_importer.as_required_str(
                        row,
                        "tamano_dimension",
                        "tamaño / dimensión",
                    ),
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
