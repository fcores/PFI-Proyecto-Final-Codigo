from datetime import date

from fastapi import UploadFile

from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.patient import Patient, PatientList
from backend.repositories.patient_repo import PatientRepository
from backend.services.excel_import_service import ExcelImportService


class PatientService:
    """Gestiona el maestro de pacientes."""

    IMPORT_ALIASES = {
        "credential_id": ["id credencial", "credencial"],
        "provider_id": ["id prestador"],
        "provider": ["prestador"],
        "first_name": ["nombre"],
        "last_name": ["apellido"],
        "birth_date": ["fecha de nacimiento", "fecha_nacimiento"],
        "gender": ["genero", "sexo"],
        "treatment": ["diagnostico", "tratamiento"],
    }

    def __init__(self, repo: PatientRepository, excel_importer: ExcelImportService) -> None:
        self._repo = repo
        self._excel_importer = excel_importer

    def create(
        self,
        *,
        credential_id: str | None,
        provider_id: str | None,
        provider: str | None,
        first_name: str,
        last_name: str,
        birth_date: date,
        gender: str,
        treatment: str | None,
        medications: list[str],
        hc_file: UploadFile | None,
        ap_file: UploadFile | None,
        img_file: UploadFile | None,
        lab_file: UploadFile | None,
        receta_file: UploadFile | None,
        otros_file: UploadFile | None,
    ) -> Patient:
        """Crea un paciente nuevo."""
        patient = Patient(
            id=self._repo.next_id(),
            credential_id=credential_id,
            provider_id=provider_id,
            provider=provider,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            gender=gender,
            treatment=treatment,
            medications=medications,
            hc_filename=hc_file.filename if hc_file else None,
            ap_filename=ap_file.filename if ap_file else None,
            img_filename=img_file.filename if img_file else None,
            lab_filename=lab_file.filename if lab_file else None,
            receta_filename=receta_file.filename if receta_file else None,
            otros_filename=otros_file.filename if otros_file else None,
        )
        return self._repo.add(patient)

    def find_by_id(self, patient_id: int) -> Patient | None:
        """Busca un paciente por ID."""
        return self._repo.find_by_id(patient_id)

    def search(self, query: str) -> list[Patient]:
        """Busca pacientes por nombre/apellido."""
        return self._repo.search(query)

    def list_all(self, limit: int = 100, offset: int = 0) -> PatientList:
        """Lista pacientes con paginacion."""
        return PatientList(patients=self._repo.list_all(limit=limit, offset=offset))

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        """Importa pacientes masivamente desde Excel."""
        rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
        errors = []
        imported_count = 0

        for index, row in enumerate(rows, start=2):
            try:
                self.create(
                    credential_id=self._excel_importer.as_optional_str(row, "credential_id"),
                    provider_id=self._excel_importer.as_optional_str(row, "provider_id"),
                    provider=self._excel_importer.as_optional_str(row, "provider"),
                    first_name=self._excel_importer.as_required_str(row, "first_name", "nombre"),
                    last_name=self._excel_importer.as_required_str(row, "last_name", "apellido"),
                    birth_date=self._excel_importer.as_required_date(row, "birth_date", "fecha de nacimiento"),
                    gender=self._excel_importer.as_required_str(row, "gender", "género"),
                    treatment=self._excel_importer.as_optional_str(row, "treatment"),
                    medications=[],
                    hc_file=None,
                    ap_file=None,
                    img_file=None,
                    lab_file=None,
                    receta_file=None,
                    otros_file=None,
                )
                imported_count += 1
            except Exception as exc:
                errors.append(BulkImportError(row_number=index, message=str(exc)))

        return BulkImportResult(
            total_rows=len(rows),
            imported_count=imported_count,
            failed_count=len(errors),
            errors=errors,
        )
