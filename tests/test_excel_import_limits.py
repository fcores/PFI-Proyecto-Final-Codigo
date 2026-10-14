"""Topes de la carga masiva por Excel."""

from io import BytesIO

import pandas as pd
import pytest
from fastapi import HTTPException

from backend.services import excel_import_service as excel_module
from backend.services.excel_import_service import ExcelImportService


def _xlsx(rows: int) -> bytes:
    buffer = BytesIO()
    pd.DataFrame({"descripcion": [f"droga {i}" for i in range(rows)]}).to_excel(buffer, index=False)
    return buffer.getvalue()


def test_rechaza_archivos_que_superan_el_tamano_maximo():
    contenido = b"PK\x03\x04" + b"0" * excel_module.MAX_IMPORT_BYTES
    with pytest.raises(HTTPException) as exc_info:
        ExcelImportService().read_rows(contenido, "grande.xlsx", {"descripcion": []})
    assert exc_info.value.status_code == 413


def test_rechaza_archivos_que_no_son_xlsx():
    with pytest.raises(HTTPException) as exc_info:
        ExcelImportService().read_rows(b"no soy un zip", "falso.xlsx", {"descripcion": []})
    assert exc_info.value.status_code == 400


def test_rechaza_demasiadas_filas(monkeypatch):
    monkeypatch.setattr(excel_module, "MAX_IMPORT_ROWS", 3)
    with pytest.raises(HTTPException) as exc_info:
        ExcelImportService().read_rows(_xlsx(4), "filas.xlsx", {"descripcion": []})
    assert exc_info.value.status_code == 413


def test_acepta_un_archivo_valido():
    rows = ExcelImportService().read_rows(_xlsx(2), "ok.xlsx", {"descripcion": []})
    assert [r["descripcion"] for r in rows] == ["droga 0", "droga 1"]


def test_potencia_con_coma_decimal_del_catalogo():
    from backend.services.medication_service import MedicationService

    svc = MedicationService.__new__(MedicationService)
    assert svc._parse_optional_float({"p": "0,9"}, "p") == 0.9
    assert svc._parse_optional_float({"p": "1.234,5"}, "p") == 1234.5
    assert svc._parse_optional_float({"p": 20.0}, "p") == 20.0
    assert svc._parse_optional_float({"p": "80-240"}, "p") is None
