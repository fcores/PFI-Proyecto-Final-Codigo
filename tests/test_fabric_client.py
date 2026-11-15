"""Cliente HTTP del puente Fabric: exito, errores de negocio, indisponibilidad y circuit breaker."""

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from backend.blockchain import fabric_client as modulo
from backend.blockchain.fabric_client import (
    CircuitBreaker,
    FabricBusinessError,
    FabricClient,
    FabricUnavailableError,
)


class _Respuesta:
    """Respuesta de urlopen como context manager."""

    def __init__(self, cuerpo):
        """Guarda el cuerpo JSON."""
        self._cuerpo = json.dumps(cuerpo).encode("utf-8")

    def read(self):
        """Devuelve el cuerpo."""
        return self._cuerpo

    def __enter__(self):
        """Entra al contexto."""
        return self

    def __exit__(self, *args):
        """Sale del contexto."""
        return False


def _error_http(codigo, cuerpo):
    """Arma un HTTPError con cuerpo opcional."""
    datos = b"" if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    return HTTPError("http://puente/invoke", codigo, "error", {}, io.BytesIO(datos))


def _urlopen_que(respuestas):
    """Devuelve un urlopen falso que entrega (o lanza) las respuestas en orden."""
    pendientes = list(respuestas)
    llamadas = []

    def _falso(req, timeout=None, context=None):
        """Simula urlopen."""
        llamadas.append(req.full_url)
        siguiente = pendientes.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return _Respuesta(siguiente)

    return _falso, llamadas


def _sin_espera(segundos):
    """Evita el backoff real en los tests."""
    return None


@pytest.fixture()
def cliente(monkeypatch):
    """Cliente apuntando a un puente ficticio, sin esperas de backoff."""
    monkeypatch.setattr(modulo.time, "sleep", _sin_espera)
    return FabricClient(base_url="http://puente", auth_token="token")


def test_invoke_y_query_exitosos(cliente, monkeypatch):
    falso, llamadas = _urlopen_que([{"tx_id": "tx1", "payload": "{}"}, {"payload": "[1]"}])
    monkeypatch.setattr(modulo, "urlopen", falso)
    assert cliente.invoke("CreatePrescription", ["a"], "prescriptor")["tx_id"] == "tx1"
    assert cliente.query("GetPrescription", ["a"]) == "[1]"
    assert llamadas == ["http://puente/invoke", "http://puente/query"]
    assert cliente.available


def test_error_de_negocio_no_se_reintenta(cliente, monkeypatch):
    falso, llamadas = _urlopen_que([_error_http(409, {"error": "ya existe", "error_type": "exists", "tx_id": "t"})])
    monkeypatch.setattr(modulo, "urlopen", falso)
    with pytest.raises(FabricBusinessError) as info:
        cliente.query("GetPrescription", ["a"])
    assert info.value.error_type == "exists"
    assert len(llamadas) == 1


def test_error_de_autenticacion_con_el_puente(cliente, monkeypatch):
    falso, _ = _urlopen_que([_error_http(401, {"error": "token", "error_type": "auth"})])
    monkeypatch.setattr(modulo, "urlopen", falso)
    with pytest.raises(FabricUnavailableError):
        cliente.query("GetPrescription", ["a"])


def test_commit_incierto_en_escritura(cliente, monkeypatch):
    falso, _ = _urlopen_que([_error_http(504, {"error": "timeout commit", "error_type": "commit_status"})])
    monkeypatch.setattr(modulo, "urlopen", falso)
    with pytest.raises(FabricUnavailableError) as info:
        cliente.invoke("AuditPrescription", ["a"], "auditor")
    assert info.value.uncertain


def test_lectura_reintenta_ante_5xx_sin_cuerpo(cliente, monkeypatch):
    falso, llamadas = _urlopen_que([_error_http(502, None), _error_http(502, None), {"payload": "ok"}])
    monkeypatch.setattr(modulo, "urlopen", falso)
    assert cliente.query("GetPrescription", ["a"]) == "ok"
    assert len(llamadas) == 3


def test_conexion_rechazada_no_es_incierta(cliente, monkeypatch):
    falso, _ = _urlopen_que([URLError(ConnectionRefusedError())])
    monkeypatch.setattr(modulo, "urlopen", falso)
    with pytest.raises(FabricUnavailableError) as info:
        cliente.invoke("CreatePrescription", ["a"], "prescriptor")
    assert not info.value.uncertain


def test_timeout_de_escritura_es_incierto(cliente, monkeypatch):
    falso, _ = _urlopen_que([OSError("timed out")])
    monkeypatch.setattr(modulo, "urlopen", falso)
    with pytest.raises(FabricUnavailableError) as info:
        cliente.invoke("CreatePrescription", ["a"], "prescriptor")
    assert info.value.uncertain


def test_sin_url_configurada():
    cliente = FabricClient(base_url="", auth_token="")
    cliente._base_url = ""
    with pytest.raises(FabricUnavailableError):
        cliente.query("GetPrescription", ["a"])
    assert cliente.health() is None
    assert not cliente.available


def test_circuit_breaker_abre_y_se_recupera(monkeypatch):
    breaker = CircuitBreaker()
    for _ in range(5):
        breaker.record_failure()
    assert breaker.is_open
    assert not breaker.allow_request()
    breaker.last_failure_time = 0.0
    assert breaker.allow_request()
    breaker.record_success()
    assert not breaker.is_open


def test_circuito_abierto_corta_el_request(cliente):
    for _ in range(5):
        cliente._circuit.record_failure()
    with pytest.raises(FabricUnavailableError):
        cliente.query("GetPrescription", ["a"])


def test_health(cliente, monkeypatch):
    falso, _ = _urlopen_que([{"status": "ok"}])
    monkeypatch.setattr(modulo, "urlopen", falso)
    assert cliente.health() == {"status": "ok"}
    falso_error, _ = _urlopen_que([OSError("caido")])
    monkeypatch.setattr(modulo, "urlopen", falso_error)
    assert cliente.health() is None
