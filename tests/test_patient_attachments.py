"""Alta de paciente: de la documentacion adjunta solo se registra el nombre."""

from datetime import date

from backend.repositories.patient_repo import PatientRepository
from backend.services.excel_import_service import ExcelImportService
from backend.services.patient_service import PatientService


def _crear(svc, **kwargs):
    base = dict(
        credential_id=None,
        provider_id=None,
        provider=None,
        first_name="Ana",
        last_name="Martinez",
        birth_date=date(1960, 1, 1),
        gender="femenino",
        treatment=None,
        medications=[],
        hc_file=None,
        ap_file=None,
        img_file=None,
        lab_file=None,
        receta_file=None,
        otros_file=None,
    )
    base.update(kwargs)
    return svc.create(**base)


def test_registra_los_nombres_enviados_sin_el_archivo(monkeypatch):
    monkeypatch.setattr(PatientRepository, "_db_available", lambda self: False)
    svc = PatientService(PatientRepository(), ExcelImportService())

    paciente = _crear(svc, filenames={"hc": "historia.pdf", "lab": "  ", "otros": None})

    assert paciente.hc_filename == "historia.pdf"
    assert paciente.lab_filename is None
    assert paciente.otros_filename is None
    assert svc.exists(paciente.id)
    assert not svc.exists(paciente.id + 100)
