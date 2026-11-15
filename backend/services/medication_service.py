"""Servicio de alta e importacion de medicamentos."""

import logging

from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.medication import Medication, MedicationList
from backend.repositories.medication_repo import MedicationRepository
from backend.repositories.monodrug_repo import MonodrugRepository
from backend.services.excel_import_service import ExcelImportService

logger = logging.getLogger(__name__)


class MedicationService:
    """Gestiona el maestro de medicamentos con todos los atributos del xlsx."""

    IMPORT_ALIASES = {
        "descripcion": ["descripcion", "descripción", "texto largo de material"],
        "ean": ["ean", "código ean/upc", "codigo ean/upc"],
        "codigo_alfabeta": [
            "codigo_alfabeta",
            "codigo alfabeta",
            "código alfabeta",
            "nro troquel alfabeta",
            "troquel",
        ],
        "tipo_conservacion": [
            "tipo_conservacion",
            "tipo conservacion",
            "tipo de conservacion",
            "cadena de frío",
            "cadena de frio",
        ],
        "laboratorio": ["laboratorio"],
        "monodroga": [
            "monodroga",
            "monodroga_id",
            "código de monodroga",
            "codigo de monodroga",
            "id monodroga",
            "id de monodroga",
        ],
        "tamano_dimension": [
            "tamano_dimension",
            "tamano dimension",
            "tamaño dimension",
            "tamaño/dimension",
            "tamaño/dimensión",
        ],
        "potencia_mg": ["potencia_mg", "valor de potencia", "potencia"],
        "unidad_potencia": [
            "unidad_potencia",
            "códigos de potencia",
            "codigos de potencia",
        ],
        "precio": ["precio", "precio de venta al publico", "precio de venta al público"],
        "via_administracion": [
            "via_administracion",
            "vía de administración",
            "via de administracion",
            "código de vías de administración",
            "codigo de vias de administracion",
        ],
    }

    def __init__(
        self,
        repo: MedicationRepository,
        monodrug_repo: MonodrugRepository,
        excel_importer: ExcelImportService,
        monodrug_service=None,
    ) -> None:
        """Inicializa el servicio de medicamentos."""
        try:
            self._repo = repo
            self._monodrug_repo = monodrug_repo
            self._excel_importer = excel_importer
            self._monodrug_service = monodrug_service
        except Exception as exc:
            logger.error("Error al inicializar MedicationService: %s", exc, exc_info=True)
            raise

    def _parse_optional_float(self, row, key):
        """Parsea un float opcional desde una fila de importacion."""
        try:
            raw = row.get(key)
            if raw is None or str(raw).strip() == "":
                return None
            if isinstance(raw, str) and "," in raw:
                # Formato es-AR del catalogo: "0,9" o "1.234,56".
                raw = raw.strip().replace(".", "").replace(",", ".")
            return float(raw)
        except Exception as exc:
            logger.warning("No se pudo parsear float opcional %s: %s", key, exc)
            return None

    def _map_tipo_conservacion(self, raw_value):
        """Mapea 'X' del xlsx a 'frio' y vacio a 'seco'."""
        try:
            val = str(raw_value).strip().upper() if raw_value else ""
            if val in ("X", "SI", "SÍ", "FRIO", "FRÍO"):
                return "frio"
            return "seco"
        except Exception as exc:
            logger.warning("Error al mapear tipo_conservacion: %s", exc)
            return "seco"

    def create(
        self,
        *,
        descripcion: str,
        ean: str,
        codigo_alfabeta: str,
        tipo_conservacion: str,
        laboratorio: str,
        monodroga: str,
        tamano_dimension: str,
        potencia_mg=None,
        unidad_potencia=None,
        precio=None,
        via_administracion=None,
    ) -> Medication:
        """Crea un medicamento con codigo autogenerado MED-XXXX."""
        try:
            mono_desc = monodroga.strip()
            existente = self._monodrug_repo.find_by_descripcion(mono_desc)
            if existente is None:
                raise ValueError(
                    "No existe la monodroga '%s' en el maestro. Creala primero en Alta de Monodrogas." % mono_desc
                )
            codigo = "MED-%04d" % (self._repo.count() + 1)
            medication = Medication(
                id=self._repo.next_id(),
                codigo=codigo,
                descripcion=descripcion,
                ean=ean,
                codigo_alfabeta=codigo_alfabeta,
                tipo_conservacion=tipo_conservacion,
                laboratorio=laboratorio,
                monodroga=mono_desc,
                tamano_dimension=tamano_dimension,
                potencia_mg=potencia_mg,
                unidad_potencia=unidad_potencia,
                precio=precio,
                via_administracion=via_administracion,
            )
            return self._repo.add(medication)
        except Exception as exc:
            logger.error("Error al crear medicamento: %s", exc, exc_info=True)
            raise

    def list_all(self) -> MedicationList:
        """Lista todos los medicamentos."""
        try:
            return MedicationList(medications=self._repo.list_all())
        except Exception as exc:
            logger.error("Error al listar medicamentos: %s", exc, exc_info=True)
            raise

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        """Importa medicamentos masivamente desde Excel.

        Si la monodroga no existe en el maestro, se auto-crea para que
        el archivo de medicamentos sea autosuficiente.
        """
        try:
            rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
            errors = []
            imported_count = 0

            for index, row in enumerate(rows, start=2):
                try:
                    mono_raw = self._excel_importer.as_required_str(
                        row,
                        "monodroga",
                        "código de monodroga",
                    )
                    if self._monodrug_service is not None:
                        self._monodrug_service.create_if_missing(mono_raw)

                    raw_conserv = row.get("tipo_conservacion", "")
                    tipo_conservacion = self._map_tipo_conservacion(raw_conserv)

                    medication = Medication(
                        id=self._repo.next_id(),
                        codigo="MED-%04d" % (self._repo.count() + 1),
                        descripcion=self._excel_importer.as_required_str(row, "descripcion", "descripción"),
                        ean=self._excel_importer.as_required_str(row, "ean"),
                        codigo_alfabeta=self._excel_importer.as_required_str(
                            row,
                            "codigo_alfabeta",
                            "nro troquel alfabeta",
                        ),
                        tipo_conservacion=tipo_conservacion,
                        laboratorio=self._excel_importer.as_required_str(row, "laboratorio"),
                        monodroga=mono_raw.strip(),
                        tamano_dimension=self._excel_importer.as_required_str(
                            row,
                            "tamano_dimension",
                            "tamaño / dimensión",
                        ),
                        potencia_mg=self._parse_optional_float(row, "potencia_mg"),
                        unidad_potencia=(
                            str(row.get("unidad_potencia")).strip()
                            if row.get("unidad_potencia") not in (None, "")
                            else None
                        ),
                        precio=self._parse_optional_float(row, "precio"),
                        via_administracion=(
                            str(row.get("via_administracion")).strip()
                            if row.get("via_administracion") not in (None, "")
                            else None
                        ),
                    )
                    self._repo.add(medication)
                    imported_count += 1
                except Exception as exc:
                    errors.append(BulkImportError(row_number=index, message=str(exc)))

            return BulkImportResult(
                total_rows=len(rows),
                imported_count=imported_count,
                failed_count=len(errors),
                errors=errors,
            )
        except Exception as exc:
            logger.error("Error en bulk_import de medicamentos: %s", exc, exc_info=True)
            raise
