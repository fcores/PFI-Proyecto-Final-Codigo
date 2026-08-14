from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import HTTPException


class ExcelImportService:
    def read_rows(self, file_bytes: bytes, filename: str, aliases: dict[str, list[str]]) -> list[dict[str, Any]]:
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Solo se admiten archivos Excel .xlsx.")

        try:
            dataframe = pd.read_excel(BytesIO(file_bytes))
        except Exception as exc:  # pragma: no cover - defensive parse guard
            raise HTTPException(status_code=400, detail="No se pudo leer el archivo Excel.") from exc

        dataframe = dataframe.dropna(how="all")
        alias_map = self._build_alias_map(aliases)

        rows: list[dict[str, Any]] = []
        for _, dataframe_row in dataframe.iterrows():
            row: dict[str, Any] = {}
            for column_name, value in dataframe_row.items():
                canonical_name = alias_map.get(self._normalize_name(str(column_name)))
                if canonical_name:
                    row[canonical_name] = self._normalize_value(value)
            rows.append(row)

        return rows

    def as_required_str(self, row: dict[str, Any], field: str, label: str | None = None) -> str:
        value = row.get(field)
        if value is None:
            raise ValueError(f"Falta el campo '{label or field}'.")
        text = str(value).strip()
        if not text:
            raise ValueError(f"El campo '{label or field}' no puede estar vacío.")
        return text

    def as_optional_str(self, row: dict[str, Any], field: str) -> str | None:
        value = row.get(field)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def as_required_int(self, row: dict[str, Any], field: str, label: str | None = None) -> int:
        value = row.get(field)
        if value is None:
            raise ValueError(f"Falta el campo '{label or field}'.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"El campo '{label or field}' debe ser numérico.") from exc

    def as_required_date(self, row: dict[str, Any], field: str, label: str | None = None) -> date:
        value = row.get(field)
        if value is None:
            raise ValueError(f"Falta el campo '{label or field}'.")

        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value.strip())
            except ValueError as exc:
                raise ValueError(f"El campo '{label or field}' debe tener formato YYYY-MM-DD.") from exc

        raise ValueError(f"El campo '{label or field}' debe ser una fecha válida.")

    def as_required_list(self, row: dict[str, Any], field: str, label: str | None = None) -> list[str]:
        value = row.get(field)
        if value is None:
            raise ValueError(f"Falta el campo '{label or field}'.")

        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = [item.strip() for item in re.split(r"[;,|]", str(value)) if item.strip()]

        if not items:
            raise ValueError(f"El campo '{label or field}' debe incluir al menos un valor.")
        return items

    def _build_alias_map(self, aliases: dict[str, list[str]]) -> dict[str, str]:
        alias_map: dict[str, str] = {}
        for canonical_name, alias_list in aliases.items():
            alias_map[self._normalize_name(canonical_name)] = canonical_name
            for alias in alias_list:
                alias_map[self._normalize_name(alias)] = canonical_name
        return alias_map

    def _normalize_name(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(character for character in normalized if not unicodedata.combining(character))
        normalized = normalized.lower().strip()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
        return normalized.strip("_")

    def _normalize_value(self, value: Any) -> Any:
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value
