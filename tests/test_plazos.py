"""Plazos de la Res. SSSalud 951/2025: 5 dias corridos y 30 dias habiles."""

from datetime import UTC, datetime

from backend.services.plazos import calcular_plazos, parsear_fecha, sumar_dias_habiles

# Lunes 5 de octubre de 2026, 10:00 UTC.
_ALTA = "2026-10-05T10:00:00Z"


def _fecha(texto):
    """Atajo para construir fechas UTC."""
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _evento(estado, timestamp):
    """Evento de auditoria minimo."""
    return {"estado_resultante": estado, "timestamp": timestamp}


def test_dias_habiles_saltean_el_fin_de_semana():
    viernes = _fecha("2026-10-09T10:00:00Z")
    assert sumar_dias_habiles(viernes, 1) == _fecha("2026-10-12T10:00:00Z")


def test_treinta_dias_habiles_son_seis_semanas():
    assert sumar_dias_habiles(_fecha(_ALTA), 30) == _fecha("2026-11-16T10:00:00Z")


def test_fecha_invalida_devuelve_none():
    assert parsear_fecha("no es una fecha") is None
    assert parsear_fecha(None) is None
    assert calcular_plazos("basura", []) is None


def test_fecha_sin_zona_se_toma_como_utc():
    assert parsear_fecha("2026-10-05T10:00:00").tzinfo is not None


def test_recien_creada_esta_en_plazo():
    plazos = calcular_plazos(_ALTA, [], ahora=_fecha("2026-10-05T12:00:00Z"))
    assert plazos["respuesta"]["estado"] == "en_plazo"
    assert plazos["respuesta"]["vence"] == "2026-10-10T10:00:00Z"
    assert plazos["respuesta"]["dias_restantes"] == 5
    assert plazos["resolucion"]["estado"] == "en_plazo"
    assert "951/2025" in plazos["norma"]


def test_respuesta_por_vencer_a_dos_dias():
    plazos = calcular_plazos(_ALTA, [], ahora=_fecha("2026-10-08T09:00:00Z"))
    assert plazos["respuesta"]["estado"] == "por_vencer"


def test_respuesta_vencida_sin_accion_del_auditor():
    plazos = calcular_plazos(_ALTA, [], ahora=_fecha("2026-10-11T00:00:00Z"))
    assert plazos["respuesta"]["estado"] == "vencido"
    assert plazos["respuesta"]["dias_restantes"] < 0


def test_respuesta_cumplida_con_la_primera_accion():
    eventos = [_evento("EN_REVISION", "2026-10-07T10:00:00Z")]
    plazos = calcular_plazos(_ALTA, eventos, ahora=_fecha("2026-10-20T00:00:00Z"))
    assert plazos["respuesta"]["estado"] == "cumplido"
    assert plazos["respuesta"]["cumplido_en"] == "2026-10-07T10:00:00Z"
    assert plazos["resolucion"]["estado"] == "en_plazo"


def test_respuesta_fuera_de_plazo():
    eventos = [_evento("EN_REVISION", "2026-10-12T10:00:00Z")]
    plazos = calcular_plazos(_ALTA, eventos, ahora=_fecha("2026-10-13T00:00:00Z"))
    assert plazos["respuesta"]["estado"] == "cumplido_fuera_de_plazo"


def test_resolucion_cumplida_con_el_dictamen():
    eventos = [
        _evento("APROBADA", "2026-10-09T10:00:00Z"),
        _evento("EN_REVISION", "2026-10-06T10:00:00Z"),
    ]
    plazos = calcular_plazos(_ALTA, eventos, ahora=_fecha("2026-12-01T00:00:00Z"))
    assert plazos["respuesta"]["cumplido_en"] == "2026-10-06T10:00:00Z"
    assert plazos["resolucion"]["estado"] == "cumplido"
    assert plazos["resolucion"]["cumplido_en"] == "2026-10-09T10:00:00Z"


def test_resolucion_vencida():
    eventos = [_evento("EN_REVISION", "2026-10-06T10:00:00Z")]
    plazos = calcular_plazos(_ALTA, eventos, ahora=_fecha("2026-11-17T00:00:00Z"))
    assert plazos["resolucion"]["estado"] == "vencido"


def test_acepta_eventos_como_modelos_y_omite_timestamps_invalidos():
    class _Evento:
        """Evento con atributos."""

        estado_resultante = "RECHAZADA"
        timestamp = "2026-10-08T10:00:00Z"

    eventos = [_Evento(), _evento("EN_REVISION", "invalido")]
    plazos = calcular_plazos(_ALTA, eventos, ahora=_fecha("2026-10-20T00:00:00Z"))
    assert plazos["resolucion"]["estado"] == "cumplido"


def test_sin_fecha_actual_usa_la_del_sistema():
    plazos = calcular_plazos(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), [])
    assert plazos["respuesta"]["estado"] == "en_plazo"
