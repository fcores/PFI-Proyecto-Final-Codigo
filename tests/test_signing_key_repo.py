"""Repositorio de claves de firma contra la base (con una conexion falsa)."""

from datetime import datetime

import pytest

from backend.repositories import signing_key_repo as modulo
from backend.repositories.signing_key_repo import SigningKeyRepository

_FILA = (1, "presc", "ECDSA-P256-SHA256", "PEM", "v1:x:y:z", "a" * 64, datetime(2026, 10, 17), None)


class _CursorFalso:
    """Cursor que registra las consultas y devuelve una fila fija."""

    def __init__(self, registro, fila):
        """Recibe la lista donde registrar y la fila a devolver."""
        self._registro = registro
        self._fila = fila

    def execute(self, sql, parametros):
        """Registra la consulta."""
        self._registro.append((sql.split()[0], parametros))

    def fetchone(self):
        """Devuelve la fila configurada."""
        return self._fila

    def __enter__(self):
        """Entra al contexto."""
        return self

    def __exit__(self, *args):
        """Sale del contexto."""
        return False


class _ConexionFalsa:
    """Conexion que entrega el cursor falso."""

    def __init__(self, registro, fila):
        """Recibe la lista donde registrar y la fila a devolver."""
        self._registro = registro
        self._fila = fila

    def cursor(self):
        """Devuelve un cursor falso."""
        return _CursorFalso(self._registro, self._fila)


@pytest.fixture()
def con_base(monkeypatch):
    """Simula base disponible; devuelve (registro, setter de fila)."""
    registro = []
    estado = {"fila": _FILA}

    class _GetDbFalso:
        """Context manager equivalente a backend.db.get_db."""

        def __enter__(self):
            """Entrega la conexion falsa."""
            return _ConexionFalsa(registro, estado["fila"])

        def __exit__(self, *args):
            """Sale del contexto."""
            return False

    def _disponible():
        """La base esta disponible."""
        return True

    monkeypatch.setattr(modulo, "is_db_available", _disponible)
    monkeypatch.setattr(modulo, "get_db", _GetDbFalso)
    return registro, estado


def test_buscar_clave_vigente_y_por_huella(con_base):
    registro, _ = con_base
    repo = SigningKeyRepository()
    assert repo.find_active("presc")["username"] == "presc"
    assert repo.find_by_fingerprint("a" * 64)["key_fingerprint"] == "a" * 64
    assert registro[0] == ("SELECT", ("presc",))


def test_sin_resultado_devuelve_none(con_base):
    _, estado = con_base
    estado["fila"] = None
    repo = SigningKeyRepository()
    assert repo.find_active("nadie") is None
    assert repo.find_by_fingerprint("b" * 64) is None


def test_insertar_y_revocar(con_base):
    registro, _ = con_base
    repo = SigningKeyRepository()
    repo.insert("presc", "ECDSA-P256-SHA256", "PEM", "v1:x:y:z", "a" * 64)
    repo.revoke("presc")
    assert [sql for sql, _ in registro] == ["INSERT", "UPDATE"]


def test_modo_en_memoria():
    repo = SigningKeyRepository()
    assert repo.find_active("presc") is None
    repo.insert("presc", "ECDSA-P256-SHA256", "PEM", "enc", "c" * 64)
    assert repo.find_by_fingerprint("c" * 64)["username"] == "presc"
    assert repo.find_by_fingerprint("d" * 64) is None
    repo.revoke("presc")
    assert repo.find_active("presc") is None
