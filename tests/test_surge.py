"""Marca de potencial recupero ante el SURGE (Res. SSSalud 731/2023, Anexo II)."""

from backend.services.surge import evaluar_surge


def _clinical(**overrides):
    """Bloque clinico minimo para la regla del SURGE."""
    base = {"edad": 61, "estadio": "IV", "m": "M1"}
    base.update(overrides)
    return base


def test_adulto_metastasico_es_potencialmente_recuperable():
    resultado = evaluar_surge(_clinical())
    assert resultado["potencialmente_recuperable"] is True
    assert resultado["a_constatar"] == ["ECOG 0-1"]
    assert "731/2023" in resultado["norma"]
    assert len(resultado["criterios_cumplidos"]) == 2


def test_menor_de_edad_no_es_recuperable():
    assert evaluar_surge(_clinical(edad=17))["potencialmente_recuperable"] is False


def test_el_limite_de_edad_es_inclusivo():
    assert evaluar_surge(_clinical(edad=18))["potencialmente_recuperable"] is True


def test_estadio_localizado_no_es_recuperable():
    resultado = evaluar_surge(_clinical(estadio="III", m="M0"))
    assert resultado["potencialmente_recuperable"] is False
    assert resultado["criterios_cumplidos"] == ["Paciente mayor de 18 años"]


def test_alcanza_con_m1_aunque_el_estadio_falte():
    assert evaluar_surge(_clinical(estadio="", m="M1a"))["potencialmente_recuperable"] is True


def test_alcanza_con_estadio_iv_en_minuscula():
    assert evaluar_surge(_clinical(estadio="ivb", m="MX"))["potencialmente_recuperable"] is True


def test_sin_edad_no_es_recuperable():
    assert evaluar_surge(_clinical(edad=None))["potencialmente_recuperable"] is False


def test_acepta_un_modelo_con_atributos():
    class _Clinico:
        """Bloque clinico con atributos en lugar de claves."""

        edad = 70
        estadio = "IV"
        m = "M1"

    assert evaluar_surge(_Clinico())["potencialmente_recuperable"] is True
