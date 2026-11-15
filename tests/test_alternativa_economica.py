"""Regla asesora de alternativa terapeutica de menor costo total (RF-33/RF-34).

Cubre las cuatro situaciones que definen el comportamiento de la regla:
  - dispara cuando existe un equivalente mas barato,
  - no dispara cuando el esquema prescrito ya es el mas economico,
  - no dispara cuando el regimen no admite equivalentes,
  - el alta exige justificacion cuando la alerta esta activa.
"""

import pytest

from backend.error_handlers import DomainError
from backend.ml.regimenes import alternativas_equivalentes, ciclos_estandar
from backend.models.prescription import PrescriptionBase
from backend.services.validation_service import ValidationService


class FakeDosisService:
    """Devuelve un costo por ciclo fijado por regimen, sin tocar la base."""

    def __init__(self, costos_por_ciclo):
        self._costos = costos_por_ciclo

    def costear_regimen(self, id_regimen, bsa, peso_kg):
        costo = self._costos.get(id_regimen)
        return [], costo

    def calcular_excedente(self, *args, **kwargs):
        return 0.0


def _prescripcion(id_regimen="R01", justificacion=None):
    return PrescriptionBase(
        patient_id=1,
        edad=61,
        sexo="F",
        peso_kg=70.5,
        talla_cm=165.0,
        diagnostico_cie10="C18.9",
        localizacion_tumor="colon ascendente",
        tipo_histologico="adenocarcinoma",
        t="T3",
        n="N1",
        m="M0",
        estadio="III",
        msi="MSS",
        ras="wild_type",
        braf_v600e="no_evaluado",
        linea_tratamiento="1L",
        id_regimen=id_regimen,
        medico_prescriptor="Dra. Perez",
        matricula="MN 12345",
        justificacion_costo=justificacion,
    )


# --------------------------------------------------------------------------
# Catalogo de equivalencias
# --------------------------------------------------------------------------


def test_regimenes_del_mismo_grupo_son_equivalentes():
    assert set(alternativas_equivalentes("R01")) == {"R02", "R03"}
    assert set(alternativas_equivalentes("R05")) == {"R06"}


def test_regimen_sin_grupo_no_admite_sustitucion():
    # La inmunoterapia no es intercambiable con un doblete de quimioterapia.
    assert alternativas_equivalentes("R09") == []
    assert alternativas_equivalentes("R00") == []


def test_los_ciclos_estandar_difieren_entre_equivalentes():
    # Es la razon por la que la comparacion se hace sobre el tratamiento
    # completo y no sobre el ciclo: 12 ciclos cada 14 dias contra 8 cada 21.
    assert ciclos_estandar("R01") == 12
    assert ciclos_estandar("R02") == 8


# --------------------------------------------------------------------------
# La regla
# --------------------------------------------------------------------------


def test_dispara_cuando_existe_equivalente_mas_barato():
    # R01: 1000 x 12 = 12.000   R02: 900 x 8 = 7.200   R03: 1200 x 12 = 14.400
    svc = ValidationService(FakeDosisService({"R01": 1000.0, "R02": 900.0, "R03": 1200.0}))
    costo, alternativas, ahorro, motivo = svc._alternativa_economica("R01", 1.8, 70.5)

    assert costo == 12000.0
    assert ahorro == 4800.0
    assert motivo is not None
    assert "R02" in motivo
    # Solo el mas barato entra; R03 es mas caro que el prescrito.
    assert [a.id_regimen for a in alternativas] == ["R02"]
    assert alternativas[0].costo_tratamiento == 7200.0
    assert alternativas[0].pct_ahorro == 40.0
    assert alternativas[0].ciclos == 8


def test_ordena_las_alternativas_por_ahorro_descendente():
    svc = ValidationService(FakeDosisService({"R03": 2000.0, "R01": 1500.0, "R02": 900.0}))
    _costo, alternativas, _ahorro, _motivo = svc._alternativa_economica("R03", 1.8, 70.5)

    assert [a.id_regimen for a in alternativas] == ["R02", "R01"]
    assert alternativas[0].ahorro > alternativas[1].ahorro


def test_no_dispara_si_el_prescrito_ya_es_el_mas_economico():
    # R02: 900 x 8 = 7.200 es el mas barato del grupo.
    svc = ValidationService(FakeDosisService({"R01": 1000.0, "R02": 900.0, "R03": 1200.0}))
    costo, alternativas, ahorro, motivo = svc._alternativa_economica("R02", 1.8, 70.5)

    assert costo == 7200.0
    assert alternativas == []
    assert ahorro is None
    assert motivo is None


def test_no_dispara_si_el_regimen_no_tiene_equivalentes():
    svc = ValidationService(FakeDosisService({"R09": 50000.0}))
    costo, alternativas, ahorro, motivo = svc._alternativa_economica("R09", 1.8, 70.5)

    assert (costo, alternativas, ahorro, motivo) == (None, [], None, None)


def test_no_dispara_sin_precios_en_catalogo():
    svc = ValidationService(FakeDosisService({"R01": None, "R02": None, "R03": None}))
    assert svc._alternativa_economica("R01", 1.8, 70.5) == (None, [], None, None)


def test_la_frecuencia_puede_invertir_la_comparacion():
    """Un esquema mas caro por ciclo puede ser mas barato por tratamiento.

    Es el nucleo del criterio planteado por el dominio: R02 cuesta mas por
    ciclo que R01 pero se administra 8 veces en lugar de 12.
    """
    svc = ValidationService(FakeDosisService({"R01": 1000.0, "R02": 1400.0, "R03": 9999.0}))
    # R01: 1000 x 12 = 12.000   R02: 1400 x 8 = 11.200
    costo, alternativas, ahorro, _motivo = svc._alternativa_economica("R01", 1.8, 70.5)

    assert costo == 12000.0
    assert [a.id_regimen for a in alternativas] == ["R02"]
    assert ahorro == 800.0


def test_la_regla_nunca_rechaza():
    """RNF-15: el hallazgo economico es asesor, el veredicto no cambia."""
    svc = ValidationService(FakeDosisService({"R01": 1000.0, "R02": 900.0, "R03": 1200.0}))
    resultado = svc.validate(_prescripcion("R01"))

    assert resultado.estado != "RECHAZADO"
    assert resultado.requiere_justificacion_costo is True
    assert resultado.ahorro_potencial == 4800.0
    assert any("alternativa terapéuticamente equivalente" in m for m in resultado.motivos)


# --------------------------------------------------------------------------
# Exigencia de justificacion en el alta
# --------------------------------------------------------------------------


class _ServicioValidacionStub:
    def __init__(self, resultado):
        self._resultado = resultado

    def validate(self, data):
        return self._resultado


def _servicio_prescripcion(resultado_validacion):
    from backend.services.prescription_service import PrescriptionService

    return PrescriptionService(
        fabric_repo=None,
        validation_service=_ServicioValidacionStub(resultado_validacion),
        dosis_service=None,
    )


def test_el_alta_falla_sin_justificacion_cuando_hay_alternativa():
    svc_val = ValidationService(FakeDosisService({"R01": 1000.0, "R02": 900.0, "R03": 1200.0}))
    resultado = svc_val.validate(_prescripcion("R01"))
    svc = _servicio_prescripcion(resultado)

    with pytest.raises(DomainError) as exc:
        svc.create(_prescripcion("R01"))

    assert exc.value.status_code == 422
    assert "justificacion_costo" in str(exc.value)


def test_el_alta_falla_con_justificacion_demasiado_corta():
    svc_val = ValidationService(FakeDosisService({"R01": 1000.0, "R02": 900.0, "R03": 1200.0}))
    resultado = svc_val.validate(_prescripcion("R01"))
    svc = _servicio_prescripcion(resultado)

    with pytest.raises(DomainError) as exc:
        svc.create(_prescripcion("R01", justificacion="  no  "))

    assert exc.value.status_code == 422


def test_el_alta_no_exige_justificacion_si_no_hay_alternativa():
    svc_val = ValidationService(FakeDosisService({"R02": 900.0, "R01": 1000.0, "R03": 1200.0}))
    resultado = svc_val.validate(_prescripcion("R02"))

    assert resultado.requiere_justificacion_costo is False
