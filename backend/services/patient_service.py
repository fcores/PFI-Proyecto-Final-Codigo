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
        filenames: dict[str, str | None] | None = None,
    ) -> Patient:
        """Crea un paciente nuevo.

        De la documentacion adjunta solo se registra el nombre del archivo
        (por UploadFile o enviado directamente en `filenames`).
        """
        filenames = filenames or {}

        def _nombre(key: str, upload: UploadFile | None) -> str | None:
            if upload is not None and upload.filename:
                return upload.filename
            value = (filenames.get(key) or "").strip()
            return value or None

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
            hc_filename=_nombre("hc", hc_file),
            ap_filename=_nombre("ap", ap_file),
            img_filename=_nombre("img", img_file),
            lab_filename=_nombre("lab", lab_file),
            receta_filename=_nombre("receta", receta_file),
            otros_filename=_nombre("otros", otros_file),
        )
        return self._repo.add(patient)

    def find_by_id(self, patient_id: int, username: str = "system") -> Patient | None:
        """Busca un paciente por ID (el acceso queda en phi_access_log)."""
        return self._repo.find_by_id(patient_id, username=username)

    def exists(self, patient_id: int) -> bool:
        """Indica si el paciente existe (sin leer PHI)."""
        return self._repo.exists(patient_id)

    def search(self, query: str, username: str = "system") -> list[Patient]:
        """Busca pacientes por nombre/apellido."""
        return self._repo.search(query, username=username)

    def list_all(self, limit: int = 100, offset: int = 0, username: str = "system") -> PatientList:
        """Lista pacientes con paginacion."""
        return PatientList(patients=self._repo.list_all(limit=limit, offset=offset, username=username))

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
