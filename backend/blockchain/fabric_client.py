"""
Cliente HTTP para fabric-gateway-svc (puente Go hacia la red Fabric).

La red Fabric es la UNICA fuente de verdad de las prescripciones, por lo que
este cliente es sincrono y distingue dos familias de errores:

- FabricUnavailableError: la red/el puente no respondieron (timeout, conexion
  rechazada, 5xx sin cuerpo JSON). Son retryables, cuentan para el circuit
  breaker y terminan en HTTP 503 hacia el usuario.
- FabricBusinessError: la red respondio pero rechazo la operacion (endorsement,
  control de acceso por MSP, transicion de estado invalida, "ya existe"...).
  NO se reintentan, NO abren el circuit breaker y se mapean a 4xx.

Transporte: si FABRIC_GATEWAY_URL es https, el certificado del puente se valida
contra la CA del proyecto (FABRIC_GATEWAY_CA_PEM, ver
fabric/scripts/gateway-tls.sh) y no contra el almacen del sistema.

Cada request lleva:
- X-Gateway-Token: auth compartida con el puente (GATEWAY_AUTH_TOKEN).
- actor: "prescriptor" | "auditor" | "prepaga" — el puente firma la transaccion
  con la identidad de la organizacion correspondiente.
"""

import json
import logging
import ssl
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.config import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 45
# Las escrituras no se reintentan y se cortan antes que el limite de
# inactividad de API Gateway (29 s): asi el 503 disenado llega al navegador en
# lugar de un 504 opaco.
_WRITE_TIMEOUT_SECONDS = 27
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_CIRCUIT_FAILURE_THRESHOLD = 5
_CIRCUIT_RECOVERY_SECONDS = 60


class FabricError(Exception):
    """Error base de la integracion con Fabric."""


class FabricUnavailableError(FabricError):
    """La red Fabric o el puente no estan disponibles (retryable).

    uncertain=True indica una escritura cuyo resultado se desconoce: el request
    llego al puente pero no hubo confirmacion del commit. Quien la invoco debe
    releer el estado antes de decidir si reintentar.
    """

    def __init__(self, message: str, uncertain: bool = False):
        super().__init__(message)
        self.uncertain = uncertain
        if uncertain:
            self.public_message = (
                "La red blockchain no confirmo la operacion a tiempo. Verifica el estado "
                "de la prescripcion antes de reintentar."
            )


class FabricBusinessError(FabricError):
    """La red respondio pero rechazo la operacion (no retryable)."""

    def __init__(self, message: str, error_type: str = "fabric", tx_id: str | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.tx_id = tx_id


@dataclass
class CircuitBreaker:
    """Circuit breaker simple: abre tras N fallos de DISPONIBILIDAD, se recupera tras TTL."""

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


def _build_ssl_context(base_url: str | None, ca_pem: str | None) -> ssl.SSLContext | None:
    """Contexto TLS para el puente, o None si la URL es http.

    Con CA configurada, solo se confia en ella (cadata reemplaza al almacen del
    sistema): un certificado publico valido para otra identidad no alcanza.
    """
    if not base_url or not base_url.lower().startswith("https://"):
        return None
    if ca_pem:
        return ssl.create_default_context(cadata=ca_pem)
    return ssl.create_default_context()


class FabricClient:
    """Cliente del puente fabric-gateway-svc."""

    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        ca_pem: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.fabric_gateway_url
        self._auth_token = auth_token or settings.gateway_auth_token
        self._ssl_context = _build_ssl_context(self._base_url, ca_pem or settings.fabric_gateway_ca_pem)
        self._circuit = CircuitBreaker()

    @property
    def available(self) -> bool:
        """Indica si el cliente tiene URL configurada y el circuit breaker permite requests."""
        return bool(self._base_url) and self._circuit.allow_request()

    def invoke(self, function: str, args: list[str], actor: str) -> dict[str, Any]:
        """Invoca una transaccion en el chaincode (submit + commit).

        Returns:
            {"tx_id": str, "payload": str} — payload es el JSON que devolvio el contrato.
        """
        return self._call(
            "/invoke",
            {"function": function, "args": args, "actor": actor},
            retry=False,
            timeout=_WRITE_TIMEOUT_SECONDS,
        )

    def query(self, function: str, args: list[str], actor: str = "prepaga") -> str:
        """Evalua una funcion de lectura sin commit. Devuelve el payload JSON."""
        result = self._call("/query", {"function": function, "args": args, "actor": actor})
        return result.get("payload") or ""

    def health(self) -> dict[str, Any] | None:
        """Estado del puente y de los peers de las tres orgs, o None si no responde.

        Timeout corto a proposito: el health check del contenedor ECS consulta
        `/`, que llama a este metodo. Si la red Fabric esta caida, el endpoint
        debe responder igual (degradado) antes de que ECS marque la task como
        unhealthy y la reinicie en loop.
        """
        if not self._base_url:
            return None
        try:
            req = Request(f"{self._base_url}/health", method="GET")
            with urlopen(req, timeout=2, context=self._ssl_context) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    # ── interno ──────────────────────────────────────────────────────────────

    def _call(
        self,
        path: str,
        body: dict[str, Any],
        retry: bool = True,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """POST al puente.

        retry=False para escrituras: AuditPrescription no es idempotente, y un
        reintento tras un commit que si se completo terminaria en "transicion
        invalida" aunque la accion haya quedado registrada.
        """
        if not self._base_url:
            raise FabricUnavailableError(
                "FABRIC_GATEWAY_URL no configurada: el backend no puede operar sin la red blockchain"
            )
        if not self._circuit.allow_request():
            raise FabricUnavailableError("Circuit breaker abierto: la red Fabric no responde")

        last_error = ""
        uncertain = False
        attempts = _MAX_RETRIES if retry else 1
        for attempt in range(attempts):
            try:
                data = json.dumps(body).encode("utf-8")
                req = Request(
                    f"{self._base_url}{path}",
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "X-Gateway-Token": self._auth_token or "",
                    },
                    method="POST",
                )
                with urlopen(req, timeout=timeout, context=self._ssl_context) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                self._circuit.record_success()
                return result

            except HTTPError as exc:
                # El puente responde errores con cuerpo JSON {error, error_type, tx_id}.
                parsed = self._parse_error_body(exc)
                if parsed is not None:
                    error_type = parsed.get("error_type", "fabric")
                    message = parsed.get("error", f"HTTP {exc.code} del puente Fabric")
                    if error_type in ("auth",):
                        raise FabricUnavailableError(
                            f"El puente Fabric rechazo la autenticacion del backend: {message}"
                        ) from exc
                    if error_type in ("commit_status",):
                        # Timeout esperando commit: el estado es incierto, se
                        # trata como indisponibilidad (el reintento con el mismo
                        # ID es seguro por idempotencia del chaincode).
                        last_error = message
                        uncertain = True
                        self._circuit.record_failure()
                    else:
                        # Error de negocio (endorsement/chaincode): no retry.
                        raise FabricBusinessError(message, error_type=error_type, tx_id=parsed.get("tx_id")) from exc
                else:
                    last_error = str(exc)
                    self._circuit.record_failure()

            except (URLError, OSError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                # Un timeout de lectura en una escritura no dice si el commit
                # ocurrio; un rechazo de conexion si (no llego a enviarse).
                refused = isinstance(getattr(exc, "reason", None), ConnectionRefusedError) or isinstance(
                    exc, ConnectionRefusedError
                )
                uncertain = uncertain or not refused
                self._circuit.record_failure()

            if attempt < attempts - 1:
                wait = _BACKOFF_BASE**attempt
                logger.warning(
                    "Fabric request fallo (intento %d/%d), reintentando en %.1fs: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    wait,
                    last_error,
                )
                time.sleep(wait)

        raise FabricUnavailableError(
            f"La red Fabric no respondio tras {attempts} intento(s): {last_error}",
            uncertain=uncertain and not retry,
        )

    @staticmethod
    def _parse_error_body(exc: HTTPError) -> dict[str, Any] | None:
        """Intenta parsear el cuerpo JSON de un HTTPError del puente."""
        try:
            body = exc.read().decode("utf-8")
            parsed = json.loads(body)
            if isinstance(parsed, dict) and parsed.get("error"):
                return parsed
        except Exception as parse_exc:
            logger.debug("Cuerpo de error del puente no parseable: %s", parse_exc)
        return None
