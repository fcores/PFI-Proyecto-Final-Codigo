"""Health check del contenedor: elige http o https segun como arranco uvicorn."""

from backend import healthcheck


class _Respuesta:
    """Respuesta minima de urlopen."""

    def __enter__(self):
        """Entra al contexto."""
        return self

    def __exit__(self, *args):
        """Sale del contexto."""
        return False


def _capturar(monkeypatch, existe_cert, error=None):
    """Parchea el entorno del health check y devuelve las llamadas a urlopen."""
    llamadas = []

    def _falso(url, timeout=None, context=None):
        """Registra la llamada."""
        llamadas.append((url, context))
        if error:
            raise error
        return _Respuesta()

    monkeypatch.setattr(healthcheck.os.path, "exists", lambda _ruta: existe_cert)
    monkeypatch.setattr(healthcheck, "urlopen", _falso)
    return llamadas


def test_sin_certificado_usa_http(monkeypatch):
    llamadas = _capturar(monkeypatch, existe_cert=False)
    assert healthcheck.main() == 0
    assert llamadas == [("http://localhost:8000/", None)]


def test_con_certificado_usa_https_sin_validar_nombre(monkeypatch):
    llamadas = _capturar(monkeypatch, existe_cert=True)
    assert healthcheck.main() == 0
    url, contexto = llamadas[0]
    assert url == "https://localhost:8000/"
    assert contexto.check_hostname is False


def test_falla_si_no_responde(monkeypatch):
    _capturar(monkeypatch, existe_cert=False, error=OSError("connection refused"))
    assert healthcheck.main() == 1
