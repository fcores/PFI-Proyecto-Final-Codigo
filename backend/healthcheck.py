"""Health check del contenedor (Dockerfile y task definition de ECS).

Sigue el mismo criterio que docker-entrypoint.sh: si uvicorn arranco con TLS
(existe /tmp/tls/cert.pem) consulta por https, si no por http. Contra
localhost no se valida el certificado, que esta emitido para el nombre que
verifica API Gateway: aca solo importa que el proceso responda.
"""

import os
import ssl
import sys
from urllib.request import urlopen

# Ruta fija dentro del contenedor, la misma que escribe docker-entrypoint.sh.
_CERT_PATH = "/tmp/tls/cert.pem"  # noqa: S108


def main() -> int:
    """Devuelve 0 si el backend responde en el puerto 8000."""
    if os.path.exists(_CERT_PATH):
        url = "https://localhost:8000/"
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    else:
        url = "http://localhost:8000/"
        context = None
    try:
        with urlopen(url, timeout=8, context=context):  # noqa: S310 - URL fija http(s)
            return 0
    except Exception as exc:  # noqa: BLE001 - cualquier fallo es "unhealthy"
        sys.stderr.write(f"healthcheck: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
