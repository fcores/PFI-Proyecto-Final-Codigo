"""Caminos de error de SURGE, plazos, panel del financiador y ahorro efectivo.

Cada funcion registra el error en el log y lo propaga: estos tests fijan que
una falla inesperada no se silencie.
"""

from datetime import UTC, datetime

import pytest

from backend.services import financiador_service, plazos, surge
from backend.services.financiador_service import FinanciadorService
from backend.services.validation_service import ValidationService
from tests.test_ahorro_efectivo import _prescripcion


class _Explota:
    """Objeto cuyo acceso a cualquier comparacion u operacion falla."""

    def __str__(self):
        """Falla al convertirse en texto."""
        raise RuntimeError("boom")

    def __int__(self):
        """Falla al convertirse en entero."""
        raise RuntimeError("boom")


class _RepoRoto:
    """Repositorio de Fabric que no responde."""

    def list(self, page_size, bookmark, actor):
        """Simula la red caida."""
        raise RuntimeError("red caida")


def test_surge_propaga_errores():
    with pytest.raises(RuntimeError):
        surge._es_avanzado_o_metastasico(_Explota(), "M0")
    with pytest.raises(RuntimeError):
        surge.evaluar_surge({"edad": _Explota()})


def test_surge_propaga_errores_al_leer_campos():
    class _Clinico(dict):
        """Bloque clinico cuyo acceso falla."""

        def get(self, campo, valor=None):
            """Falla al leerse."""
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        surge._valor(_Clinico(), "edad")


def test_plazos_propagan_errores():
    with pytest.raises(TypeError):
        plazos.sumar_dias_habiles("no es fecha", 1)
    with pytest.raises(AttributeError):
        plazos._formatear("no es fecha")
    with pytest.raises(AttributeError):
        plazos.evaluar_plazo("no es fecha", None, datetime.now(UTC))
    with pytest.raises(TypeError):
        plazos._primer_evento(42)
    assert plazos._formatear(None) is None


def test_calcular_plazos_propaga_errores(monkeypatch):
    def _falla(*_args):
        """Simula un error interno."""
        raise RuntimeError("boom")

    monkeypatch.setattr(plazos, "sumar_dias_habiles", _falla)
    with pytest.raises(RuntimeError):
        plazos.calcular_plazos("2026-10-05T10:00:00Z", [])


def test_el_panel_propaga_la_caida_de_la_red(monkeypatch):
    monkeypatch.setenv("FINANCIADOR_MAX_PRESCRIPCIONES", "10")
    servicio = FinanciadorService(_RepoRoto())
    with pytest.raises(RuntimeError):
        servicio.resumen()
    with pytest.raises(RuntimeError):
        servicio.expedientes()


def test_el_panel_propaga_errores_internos(monkeypatch):
    def _falla(*_args):
        """Simula un error interno."""
        raise RuntimeError("boom")

    monkeypatch.setattr(financiador_service, "evaluar_surge", _falla)
    with pytest.raises(AttributeError):
        financiador_service.plazo_vigente(42)
    monkeypatch.setattr(financiador_service.os, "getenv", _falla)
    with pytest.raises(RuntimeError):
        financiador_service._tope_prescripciones()


def test_el_expediente_propaga_errores():
    with pytest.raises(AttributeError):
        FinanciadorService(None)._expediente(object())


def test_el_ahorro_efectivo_propaga_errores():
    class _DosisRota:
        """Catalogo que falla al costear."""

        def costear_regimen(self, *_args):
            """Simula el catalogo caido."""
            raise RuntimeError("catalogo caido")

        def calcular_excedente(self, *_args):
            """Sin excedente."""
            return 0.0

    servicio = ValidationService(_DosisRota())
    with pytest.raises(RuntimeError):
        servicio._costo_tratamiento("R01", 1.8, 70.5)
    with pytest.raises(RuntimeError):
        servicio._ahorro_efectivo(_prescripcion("R02", regimen_original="R01"))
    with pytest.raises(RuntimeError):
        servicio.validate(_prescripcion("R02"))
