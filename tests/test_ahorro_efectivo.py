"""Ahorro efectivo por adoptar la alternativa equivalente de menor costo (RF-43)."""

from backend.models.prescription import PrescriptionBase
from backend.services.validation_service import ValidationService
from tests.test_alternativa_economica import FakeDosisService

# R01: 1000 x 12 = 12.000   R02: 900 x 8 = 7.200   R03: 1200 x 12 = 14.400
_COSTOS = {"R01": 1000.0, "R02": 900.0, "R03": 1200.0}


def _prescripcion(id_regimen, regimen_original=None, **overrides):
    """Prescripcion de estadio III con el regimen dado."""
    base = dict(
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
        regimen_original=regimen_original,
    )
    base.update(overrides)
    return PrescriptionBase(**base)


def _servicio():
    """Motor con costos por ciclo fijos."""
    return ValidationService(FakeDosisService(_COSTOS))


def test_registra_el_ahorro_al_adoptar_la_alternativa():
    resultado = _servicio().validate(_prescripcion("R02", regimen_original="R01"))
    assert resultado.regimen_original == "R01"
    assert resultado.ahorro_efectivo == 4800.0


def test_sin_regimen_original_no_hay_ahorro_efectivo():
    resultado = _servicio().validate(_prescripcion("R02"))
    assert resultado.regimen_original is None
    assert resultado.ahorro_efectivo is None


def test_regimen_original_igual_al_actual_se_ignora():
    resultado = _servicio().validate(_prescripcion("R02", regimen_original="R02"))
    assert resultado.ahorro_efectivo is None


def test_un_regimen_no_equivalente_no_genera_ahorro():
    resultado = _servicio().validate(_prescripcion("R02", regimen_original="R09"))
    assert resultado.ahorro_efectivo is None


def test_una_alternativa_mas_cara_no_genera_ahorro():
    resultado = _servicio().validate(
        _prescripcion("R03", regimen_original="R01", justificacion_costo="Toxicidad previa a oxaliplatino")
    )
    assert resultado.ahorro_efectivo is None


def test_sin_catalogo_de_costos_no_hay_ahorro():
    resultado = ValidationService().validate(_prescripcion("R02", regimen_original="R01"))
    assert resultado.ahorro_efectivo is None


def test_el_veredicto_incluye_la_marca_surge():
    resultado = _servicio().validate(_prescripcion("R02"))
    assert resultado.surge["potencialmente_recuperable"] is False
    metastasico = _servicio().validate(_prescripcion("R02", estadio="IV", m="M1"))
    assert metastasico.surge["potencialmente_recuperable"] is True
