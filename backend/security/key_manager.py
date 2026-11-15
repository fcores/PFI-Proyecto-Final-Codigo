"""
Gestion de la clave maestra de cifrado.

En produccion: carga desde AWS Secrets Manager via boto3 con cache y TTL.
En local/test: acepta una clave de desarrollo via variable de entorno
ENCRYPTION_KEY_DEV (base64, solo para desarrollo).
"""

import base64
import json
import logging
import time

from backend.config import get_settings
from backend.security.crypto import CryptoService

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300  # 5 minutos
_cached_service: CryptoService | None = None
_cache_timestamp: float = 0.0


def _load_from_secrets_manager(secret_arn: str) -> tuple[bytes, str]:
    """Carga la clave maestra desde AWS Secrets Manager.

    El secreto debe contener un JSON con estructura:
    {"v1": "<clave_b64>", "activa": "v1"}

    Returns:
        Tuple de (clave_bytes, version_activa)
    """
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
        secret_data = json.loads(response["SecretString"])
        active_version = secret_data.get("activa", "v1")
        key_b64 = secret_data[active_version]
        key_bytes = base64.b64decode(key_b64)
        if len(key_bytes) != 32:
            raise ValueError(f"La clave version '{active_version}' no tiene 32 bytes")
        return key_bytes, active_version
    except ClientError as e:
        logger.error("Error al leer secreto de cifrado: %s", e.response["Error"]["Code"])
        raise RuntimeError("No se pudo obtener la clave de cifrado de Secrets Manager") from e


def _load_dev_key() -> tuple[bytes, str]:
    """Carga la clave de desarrollo desde la variable de entorno."""
    settings = get_settings()
    key_b64 = settings.encryption_key_dev
    if not key_b64:
        raise RuntimeError(
            "ENCRYPTION_KEY_DEV no configurada. "
            'Generar con: python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"'
        )
    key_bytes = base64.b64decode(key_b64)
    if len(key_bytes) != 32:
        raise ValueError("ENCRYPTION_KEY_DEV debe ser 32 bytes en base64")
    return key_bytes, "dev"


def get_crypto_service() -> CryptoService:
    """Retorna el servicio de cifrado con la clave activa (cacheado con TTL)."""
    global _cached_service, _cache_timestamp

    now = time.time()
    if _cached_service and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
        return _cached_service

    settings = get_settings()

    if settings.encryption_secret_arn:
        key_bytes, version = _load_from_secrets_manager(settings.encryption_secret_arn)
    elif settings.environment in ("local", "test"):
        key_bytes, version = _load_dev_key()
    else:
        raise RuntimeError(
            "ENCRYPTION_SECRET_ARN requerido en produccion/staging. " "En local/test usar ENCRYPTION_KEY_DEV."
        )

    _cached_service = CryptoService(key_bytes, key_version=version)
    _cache_timestamp = now
    logger.info("Clave de cifrado cargada (version: %s)", version)
    return _cached_service
