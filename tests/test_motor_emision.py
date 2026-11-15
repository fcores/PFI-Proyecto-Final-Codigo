"""Motor de emision: dosis, presentaciones, guias, reglas, codificacion y validacion hibrida."""

import pandas as pd

from backend.ml import codificacion, guias, regimenes, reglas
from backend.ml.dosis import calcular_dosis_mg, resolver_presentaciones
from backend.ml.feature_mapper import mapear_linea, mapear_sexo, prescription_a_datos_modelo
from backend.models.prescription import PrescriptionBase
from backend.services.dosis_service import DosisService
from backend.services.validation_service import ValidationService


class _Medicamento:
    """Presentacion comercial minima del catalogo."""

    def __init__(self, potencia_mg, precio, via="INYECTABLE IV", ean="779"):
        """Arma la presentacion."""
        self.potencia_mg = potencia_mg
        self.precio = precio
        self.ean = ean
        self.via_administracion = via


class _CatalogoFake:
    """Repositorio de medicamentos en memoria."""

    def __init__(self, por_monodroga):
        """Recibe {monodroga: [presentaciones]}."""
        self._datos = por_monodroga

    def find_by_monodroga(self, farmaco):
        """Devuelve las presentaciones de la monodroga."""
        return self._datos.get(farmaco, [])


_CATALOGO = {
    "oxaliplatino": [_Medicamento(50, 100.0), _Medicamento(100, 180.0)],
    "fluorouracilo": [_Medicamento(500, 20.0)],
    "leucovorina": [_Medicamento(50, 10.0)],
    "capecitabina": [_Medicamento(500, 5.0, via="ORAL")],
    "irinotecan": [_Medicamento(100, 90.0)],
    "cetuximab": [_Medicamento(100, 400.0), _Medicamento(500, 1900.0)],
}


def _prescripcion(**overrides):
    """Prescripcion base de estadio III para el motor."""
    base = dict(
        patient_id=1,
        edad=61,
        sexo="Femenino",
        peso_kg=70.0,
        talla_cm=165.0,
        diagnostico_cie10="C18.7",
        localizacion_tumor="colon izquierdo",
        tipo_histologico="Adenocarcinoma",
        t="T3",
        n="N1",
        m="M0",
        estadio="III",
        msi="MSS",
        ras="wild_type",
        braf_v600e="wild_type",
        linea_tratamiento="primera",
        id_regimen="R01",
        medico_prescriptor="Dra. Perez",
        matricula="MN 12345",
    )
    base.update(overrides)
    return PrescriptionBase(**base)


# ── dosis y presentaciones ──────────────────────────────────────────────────


def test_dosis_segun_la_base_de_cada_farmaco():
    assert calcular_dosis_mg("oxaliplatino", 2.0, 70, "R01") == 170
    assert calcular_dosis_mg("oxaliplatino", 2.0, 70, "R02") == 260
    assert calcular_dosis_mg("bevacizumab", 2.0, 70, "R07") == 350
    assert calcular_dosis_mg("pembrolizumab", 2.0, 70, "R09") == 200
    assert calcular_dosis_mg("desconocido", 2.0, 70, "R01") == 0.0


def test_presentaciones_de_minimo_excedente():
    pres = [{"potencia_mg": 50, "precio": 100, "via": "INYECTABLE IV"}, {"potencia_mg": 100, "precio": 180}]
    resultado = resolver_presentaciones(140, "oxaliplatino", pres)
    assert resultado["mg_cubiertos"] == 150
    assert resultado["excedente_mg"] == 10


def test_presentaciones_vacias_o_de_otra_via():
    assert resolver_presentaciones(100, "oxaliplatino", [])["presentaciones"] == []
    solo_orales = [{"potencia_mg": 500, "precio": 5, "via": "ORAL"}]
    assert resolver_presentaciones(100, "oxaliplatino", solo_orales)["mg_cubiertos"] == 0
    sin_precio = [{"potencia_mg": 500, "precio": None}]
    assert resolver_presentaciones(100, "oxaliplatino", sin_precio)["mg_cubiertos"] == 0


def test_dosis_service_referencia_costeo_y_excedente():
    svc = DosisService(_CatalogoFake(_CATALOGO))
    refs = svc.dosis_referencia_regimen("R02", 1.8, 70)
    assert refs[0] == {"monodroga": "oxaliplatino", "dosis_mg": 234.0}

    costos, total = svc.costear_regimen("R02", 1.8, 70)
    assert total is not None and total > 0
    assert costos[0].presentaciones_usadas > 0

    _, sin_catalogo = DosisService(_CatalogoFake({})).costear_regimen("R09", 1.8, 70)
    assert sin_catalogo is None

    exacto = svc.calcular_excedente("R01", [{"monodroga": "oxaliplatino", "dosis_mg": 150.0}], 1.8, 70)
    assert exacto == 0.0
    excedido = DosisService(_CatalogoFake({})).calcular_excedente(
        "R01", [{"monodroga": "oxaliplatino", "dosis_mg": 300.0}], 1.8, 70
    )
    assert excedido > 0.2
    assert svc.calcular_excedente("R01", [], 1.8, 70) == 0.0


def test_excedente_con_dosis_como_modelos():
    from backend.models.prescription import DosisFarmaco

    svc = DosisService(_CatalogoFake(_CATALOGO))
    dosis = [DosisFarmaco(monodroga="oxaliplatino", dosis_mg=140.0)]
    assert svc.calcular_excedente("R01", dosis, 1.8, 70) > 0
    con_dosis = _prescripcion(dosis_por_farmaco=[{"monodroga": "oxaliplatino", "dosis_mg": 1}])
    datos = prescription_a_datos_modelo(con_dosis, 1.8, 0)
    assert datos["n_farmacos"] == 1


def test_alternativa_economica_sin_precio_del_equivalente():
    class _CostosParciales:
        """Solo el regimen prescrito tiene precio."""

        def costear_regimen(self, id_regimen, bsa, peso_kg):
            """Devuelve costo solo para R01."""
            if id_regimen == "R01":
                return [], 100.0
            return [], None

        def calcular_excedente(self, *args):
            """Sin excedente."""
            return 0.0

    resultado = ValidationService(_CostosParciales()).validate(_prescripcion())
    assert resultado.alternativas_economicas == []
    assert resultado.costo_tratamiento == 1200.0


# ── reglas y guias ──────────────────────────────────────────────────────────


def test_reglas_deterministicas():
    assert reglas.aplicar_reglas({"ras": "mutado", "tiene_anti_egfr": 1})
    assert reglas.aplicar_reglas({"msi": "MSS", "es_inmunoterapia": 1})
    assert reglas.aplicar_reglas({"estadio": 1, "n_farmacos": 2, "id_regimen": "R06"})
    assert reglas.aplicar_reglas({"m": "M1", "estadio": 1})
    assert reglas.aplicar_reglas({"excedente_relativo": 0.35})
    assert reglas.aplicar_reglas({"estadio": 3, "excedente_relativo": 0.1}) == []


_CASOS_GUIAS = [
    ({"estadio": 1}, "R00"),
    ({"estadio": 2, "t": 3, "ganglios_examinados": 15, "lvi": 0, "pni": 0}, "R00"),
    ({"estadio": 2, "t": 4, "ganglios_examinados": 8, "lvi": 1, "pni": 1}, "R06"),
    ({"estadio": 3}, "R01"),
    ({"estadio": 4, "msi": "MSI-H"}, "R09"),
    ({"estadio": 4, "braf_v600e": "presente"}, "R10"),
    ({"estadio": 4, "ras": "mutado"}, "R07"),
    ({"estadio": 4, "ras": "wild_type", "lateralidad": "izquierdo"}, "R08"),
    ({"estadio": 4, "ras": "wild_type", "lateralidad": "derecho"}, "R07"),
    ({"estadio": 4, "ras": "wild_type", "lateralidad": "transverso"}, "R07"),
]


def test_arbol_de_las_guias():
    for datos, esperado in _CASOS_GUIAS:
        id_regimen, _base, aplicadas = guias.regimen_por_guias(datos)
        assert id_regimen == esperado, datos
        assert aplicadas


# ── catalogo de regimenes ───────────────────────────────────────────────────


def test_catalogo_de_regimenes():
    assert regimenes.nombre_regimen("R02") == "CAPEOX"
    assert regimenes.nombre_regimen("R99") == "R99"
    assert regimenes.farmacos_regimen("R99") == []
    assert regimenes.farmacos_regimen("R07", base_regimen="R03")[0] == "irinotecan"
    assert regimenes.ciclos_estandar("R99") == 1
    flags = regimenes.flags_regimen("R10")
    assert flags["es_dirigido"] == 1 and flags["tiene_anti_egfr"] == 1
    assert regimenes.calcular_excedente_relativo(10, 0) == 0.0
    assert regimenes.calcular_excedente_relativo(10, 100) == 0.1


# ── codificacion ────────────────────────────────────────────────────────────


def test_colapsadores_tnm_y_estadio():
    assert codificacion.colapsar_t("Tis") == 0
    assert codificacion.colapsar_t("T4b") == 4
    assert codificacion.colapsar_t(None) is None
    assert codificacion.colapsar_t("X") is None
    assert codificacion.colapsar_n("N2a") == 2
    assert codificacion.colapsar_n(None) is None
    assert codificacion.colapsar_m("MX") == "MX"
    assert codificacion.colapsar_m("M1c") == "M1"
    assert codificacion.colapsar_m("M0") == "M0"
    assert codificacion.colapsar_m("?") is None
    assert codificacion.colapsar_m(None) is None
    assert codificacion.colapsar_estadio("Stage IVA") == 4
    assert codificacion.colapsar_estadio("IIIB") == 3
    assert codificacion.colapsar_estadio("IIA") == 2
    assert codificacion.colapsar_estadio("I") == 1
    assert codificacion.colapsar_estadio("0") is None
    assert codificacion.colapsar_estadio(None) is None


def test_histologia_y_categorias():
    assert codificacion.histologia_agrupada("Adenocarcinoma mucinoso") == "mucinoso"
    assert codificacion.histologia_agrupada("Adenocarcinoma") == "adenocarcinoma_nos"
    assert codificacion.histologia_agrupada("Carcinoma medular") == "otros"
    assert codificacion.histologia_agrupada(None) is None
    assert codificacion.normalizar_valor_categorico("braf_v600e", "ausente") == "wild_type"
    assert codificacion.normalizar_valor_categorico("msi", float("nan")) is None
    assert codificacion.normalizar_valor_categorico("msi", None) is None
    assert codificacion.codificar_categorica("msi", "MSI-H") == 1
    assert codificacion.codificar_categorica("columna_inexistente", "x") == -1
    assert codificacion.codificar_categorica("msi", None) == -1


def test_preparar_features_dict_y_dataframe():
    features = codificacion.preparar_features({"edad": "70", "t": "no-numerico", "msi": "MSS"})
    assert features["edad"] == 70.0
    assert features["t"] == -1
    assert features["msi"] == 0
    assert features["ras"] == -1

    df = pd.DataFrame({"edad": [60, 70], "msi": ["MSS", "MSI-H"]})
    matriz = codificacion.preparar_features_dataframe(df)
    assert list(matriz["msi"]) == [0, 1]
    assert list(matriz["ras"]) == [-1, -1]


def test_mapeos_del_formulario():
    assert mapear_sexo("Masculino") == "male"
    assert mapear_sexo(None) is None
    assert mapear_linea(None) == 1
    assert mapear_linea(2) == 2
    assert mapear_linea("tercera") == 3
    crudo = {"id_regimen": "R08", "dosis_por_farmaco": [{"monodroga": "cetuximab"}]}
    datos = prescription_a_datos_modelo(crudo, 1.8, 0)
    assert datos["tiene_anti_egfr"] == 1


# ── validacion hibrida ──────────────────────────────────────────────────────


def test_completitud_rechaza_estadio_iv_sin_m1():
    resultado = ValidationService().validate(_prescripcion(estadio="IV", m="M0"))
    assert resultado.estado == "RECHAZADO"
    assert resultado.origen == "reglas"


def test_completitud_rechaza_estadio_localizado_con_m1():
    resultado = ValidationService().validate(_prescripcion(estadio="III", m="M1"))
    assert resultado.estado == "RECHAZADO"


def test_regla_rechaza_anti_egfr_con_ras_mutado():
    resultado = ValidationService(DosisService(_CatalogoFake(_CATALOGO))).validate(
        _prescripcion(estadio="IV", m="M1", ras="mutado", id_regimen="R08")
    )
    assert resultado.estado == "RECHAZADO"
    assert any("RAS" in motivo for motivo in resultado.motivos)
    assert resultado.regimen_sugerido == "R07"


def test_el_modelo_emite_veredicto_y_aportes():
    resultado = ValidationService(DosisService(_CatalogoFake(_CATALOGO))).validate(_prescripcion())
    assert resultado.estado in ("APROBADO", "REVISION")
    assert resultado.origen == "modelo"
    assert resultado.probabilidad_concordante is not None
    assert resultado.nivel_confianza in ("alta", "media", "baja")


def test_sin_modelo_se_deriva_a_revision(monkeypatch):
    from backend.services import validation_service as modulo

    def _no_disponible():
        """Simula el artefacto ausente."""
        return False

    monkeypatch.setattr(modulo, "modelo_disponible", _no_disponible)
    resultado = ValidationService().validate(_prescripcion(id_regimen="R02"))
    assert resultado.estado == "REVISION"
    assert resultado.origen == "reglas"


def test_nivel_de_confianza():
    svc = ValidationService()
    assert svc._nivel_confianza(None, 0.4, 0.7) == "desconocido"
    assert svc._nivel_confianza(0.9, 0.4, 0.7) == "alta"
    assert svc._nivel_confianza(0.1, 0.4, 0.7) == "baja"
    assert svc._nivel_confianza(0.5, 0.4, 0.7) == "media"
