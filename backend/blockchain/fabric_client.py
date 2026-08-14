"""
Cliente HTTP para comunicarse con fabric-gateway-svc (sidecar Go en la EC2 Fabric).

Implementa:
- Reintentos con backoff exponencial.
- Circuit breaker basico (abre tras N fallos consecutivos, se cierra tras un TTL).
- Timeouts configurables.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.config import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_CIRCUIT_FAILURE_THRESHOLD = 5
_CIRCUIT_RECOVERY_SECONDS = 60


@dataclass
class CircuitBreaker:
    """Circuit breaker simple: abre tras N fallos, se recupera tras TTL."""

    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= _CIRCUIT_FAILURE_THRESHOLD:
            self.is_open = True
            logger.warning("Circuit breaker ABIERTO tras %d fallos consecutivos", self.failure_count)

    def record_success(self) -> None:
        self.failure_count = 0
        if self.is_open:
            self.is_open = False
            logger.info("Circuit breaker CERRADO tras exito")

    def allow_request(self) -> bool:
        if not self.is_open:
            return True
        elapsed = time.time() - self.last_failure_time
        if elapsed >= _CIRCUIT_RECOVERY_SECONDS:
            logger.info("Circuit breaker en half-open, intentando recovery")
            return True
        return False


@dataclass
class FabricResponse:
    """Respuesta del sidecar fabric-gateway-svc."""

    tx_id: str | None = None
    payload: str | None = None
    error: str | None = None
    success: bool = True


class FabricClient:
    """Cliente para el sidecar fabric-gateway-svc."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or get_settings().fabric_gateway_url
        self._circuit = CircuitBreaker()

    @property
    def available(self) -> bool:
        """Indica si el cliente tiene URL configurada y el circuit breaker permite requests."""
        return bool(self._base_url) and self._circuit.allow_request()

    def invoke(self, function: str, args: list[str]) -> FabricResponse:
        """Invoca una transaccion en el chaincode (con commit)."""
        return self._call("/invoke", {"function": function, "args": args})

    def query(self, function: str, args: list[str]) -> FabricResponse:
        """Ejecuta una query sin commit."""
        return self._call("/query", {"function": function, "args": args})

    def health(self) -> bool:
        """Verifica si el sidecar esta disponible."""
        try:
            req = Request(f"{self._base_url}/health", method="GET")
            with urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _call(self, path: str, body: dict[str, Any]) -> FabricResponse:
        """Ejecuta una llamada HTTP con reintentos y backoff."""
        if not self._base_url:
            return FabricResponse(success=False, error="FABRIC_GATEWAY_URL no configurada")

        if not self._circuit.allow_request():
            return FabricResponse(success=False, error="Circuit breaker abierto: Fabric no disponible temporalmente")

        last_error = ""
        for attempt in range(_MAX_RETRIES):
            try:
                data = json.dumps(body).encode("utf-8")
                req = Request(
                    f"{self._base_url}{path}",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
                    result = json.loads(resp.read().decode("utf-8"))

                if result.get("error"):
                    self._circuit.record_failure()
                    return FabricResponse(success=False, error=result["error"])

                self._circuit.record_success()
                return FabricResponse(
                    tx_id=result.get("tx_id"),
                    payload=result.get("payload"),
                    success=True,
                )

            except (URLError, HTTPError, OSError) as exc:
                last_error = str(exc)
                self._circuit.record_failure()
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE**attempt
                    logger.warning(
                        "Fabric request fallo (intento %d/%d), reintentando en %.1fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                        last_error,
                    )
                    time.sleep(wait)

        return FabricResponse(success=False, error=f"Agotados reintentos: {last_error}")


_client: FabricClient | None = None


def get_fabric_client() -> FabricClient:
    """Retorna el singleton del cliente Fabric."""
    global _client
    if _client is None:
        _client = FabricClient()
    return _client
