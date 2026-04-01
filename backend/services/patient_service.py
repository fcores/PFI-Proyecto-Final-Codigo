from datetime import date
from typing import List, Optional

from fastapi import UploadFile

from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.patient import Patient, PatientList
from backend.repositories.patient_repo import PatientRepository
from backend.services.excel_import_service import ExcelImportService


class PatientService:
    IMPORT_ALIASES = {
        "sap_id": ["id paciente sap", "sap", "id sap paciente"],
        "credential_id": ["id credencial", "credencial"],
        "provider_id": ["id prestador"],
        "provider": ["prestador"],
        "first_name": ["nombre"],
        "last_name": ["apellido"],
        "birth_date": ["fecha de nacimiento", "fecha_nacimiento"],
        "gender": ["genero", "sexo"],
        "treatment": ["diagnostico", "tratamiento"],
        "tipo_empadronamiento": ["tipo de empadronamiento", "tipo_empadronamiento"],
        "fecha_inicio": ["fecha de inicio", "fecha_inicio"],
        "fecha_primera_toma": ["fecha de primera toma", "fecha_primera_toma"],
        "cadencia_estimada_toma": ["cadencia estimada", "cadencia estimada toma", "cadencia_estimada_toma"],
    }

    def __init__(self, repo: PatientRepository, excel_importer: ExcelImportService) -> None:
        self._repo = repo
        self._excel_importer = excel_importer

    def create(
        self,
        *,
        sap_id: str,
        credential_id: Optional[str],
        provider_id: Optional[str],
        provider: Optional[str],
        first_name: str,
        last_name: str,
        birth_date: date,
        gender: str,
        treatment: Optional[str],
        medications: List[str],
        tipo_empadronamiento: str,
        fecha_inicio: date,
        fecha_primera_toma: date,
        cadencia_estimada_toma: int,
        hc_file: Optional[UploadFile],
        ap_file: Optional[UploadFile],
        img_file: Optional[UploadFile],
        lab_file: Optional[UploadFile],
        receta_file: Optional[UploadFile],
        otros_file: Optional[UploadFile],
    ) -> Patient:
        patient = Patient(
            id=self._repo.next_id(),
            sap_id=sap_id,
            credential_id=credential_id,
            provider_id=provider_id,
            provider=provider,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            gender=gender,
            treatment=treatment,
            medications=medications,
            tipo_empadronamiento=tipo_empadronamiento,
            fecha_inicio=fecha_inicio,
            fecha_primera_toma=fecha_primera_toma,
            cadencia_estimada_toma=cadencia_estimada_toma,
            hc_filename=hc_file.filename if hc_file else None,
            ap_filename=ap_file.filename if ap_file else None,
            img_filename=img_file.filename if img_file else None,
            lab_filename=lab_file.filename if lab_file else None,
            receta_filename=receta_file.filename if receta_file else None,
            otros_filename=otros_file.filename if otros_file else None,
        )
        return self._repo.add(patient)

    def list_all(self) -> PatientList:
        return PatientList(patients=self._repo.list_all())

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
        errors: list[BulkImportError] = []
        imported_count = 0

        for index, row in enumerate(rows, start=2):
            try:
                self.create(
                    sap_id=self._excel_importer.as_required_str(row, "sap_id", "sap_id"),
                    credential_id=self._excel_importer.as_optional_str(row, "credential_id"),
                    provider_id=self._excel_importer.as_optional_str(row, "provider_id"),
                    provider=self._excel_importer.as_optional_str(row, "provider"),
                    first_name=self._excel_importer.as_required_str(row, "first_name", "nombre"),
                    last_name=self._excel_importer.as_required_str(row, "last_name", "apellido"),
                    birth_date=self._excel_importer.as_required_date(row, "birth_date", "fecha de nacimiento"),
                    gender=self._excel_importer.as_required_str(row, "gender", "género"),
                    treatment=self._excel_importer.as_optional_str(row, "treatment"),
                    medications=[],
                    tipo_empadronamiento=self._excel_importer.as_required_str(
                        row,
                        "tipo_empadronamiento",
                        "tipo de empadronamiento",
                    ),
                    fecha_inicio=self._excel_importer.as_required_date(row, "fecha_inicio", "fecha de inicio"),
                    fecha_primera_toma=self._excel_importer.as_required_date(
                        row,
                        "fecha_primera_toma",
                        "fecha de primera toma",
                    ),
                    cadencia_estimada_toma=self._excel_importer.as_required_int(
                        row,
                        "cadencia_estimada_toma",
                        "cadencia estimada de toma",
                    ),
                    hc_file=None,
                    ap_file=None,
                    img_file=None,
                    lab_file=None,
                    receta_file=None,
                    otros_file=None,
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
