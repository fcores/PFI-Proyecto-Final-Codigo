"""Servicio de alta e importacion de monodrogas."""
import logging

from backend.models.bulk_import import BulkImportError, BulkImportResult
from backend.models.monodrug import Monodrug, MonodrugList
from backend.repositories.monodrug_repo import MonodrugRepository
from backend.services.excel_import_service import ExcelImportService

logger = logging.getLogger(__name__)


class MonodrugService:
    """Gestiona el maestro de monodrogas con codigo autogenerado."""

    IMPORT_ALIASES = {
        "descripcion": ["descripcion", "descripción", "código de monodroga", "codigo de monodroga", "monodroga"],
    }

    def __init__(self, repo: MonodrugRepository, excel_importer: ExcelImportService) -> None:
        """Inicializa el servicio de monodrogas."""
        try:
            self._repo = repo
            self._excel_importer = excel_importer
        except Exception as exc:
            logger.error("Error al inicializar MonodrugService: %s", exc, exc_info=True)
            raise

    def create(self, *, descripcion: str) -> Monodrug:
        """Crea una monodroga con codigo autogenerado MONO-XXXX."""
        try:
            desc = descripcion.strip()
            if not desc:
                raise ValueError("La descripción de la monodroga no puede estar vacía.")
            existente = self._repo.find_by_descripcion(desc)
            if existente is not None:
                raise ValueError("Ya existe una monodroga con la descripción '%s'." % desc)
            next_id = self._repo.next_id()
            codigo = "MONO-%04d" % (self._repo.count() + 1)
            monodrug = Monodrug(id=next_id, descripcion=desc, codigo=codigo)
            return self._repo.add(monodrug)
        except Exception as exc:
            logger.error("Error al crear monodroga: %s", exc, exc_info=True)
            raise

    def create_if_missing(self, descripcion: str) -> Monodrug:
        """Crea la monodroga si no existe; retorna la existente si ya esta."""
        try:
            desc = descripcion.strip()
            existente = self._repo.find_by_descripcion(desc)
            if existente is not None:
                return existente
            return self.create(descripcion=desc)
        except Exception as exc:
            logger.error("Error en create_if_missing para '%s': %s", descripcion, exc, exc_info=True)
            raise

    def list_all(self) -> MonodrugList:
        """Lista todas las monodrogas."""
        try:
            return MonodrugList(monodrugs=self._repo.list_all())
        except Exception as exc:
            logger.error("Error al listar monodrogas: %s", exc, exc_info=True)
            raise

    def bulk_import(self, file_bytes: bytes, filename: str) -> BulkImportResult:
        """Importa monodrogas masivamente desde Excel."""
        try:
            rows = self._excel_importer.read_rows(file_bytes, filename, self.IMPORT_ALIASES)
            errors = []
            imported_count = 0

            for index, row in enumerate(rows, start=2):
                try:
                    self.create(
                        descripcion=self._excel_importer.as_required_str(row, "descripcion", "descripción"),
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
        except Exception as exc:
            logger.error("Error en bulk_import de monodrogas: %s", exc, exc_info=True)
            raise
