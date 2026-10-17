"""
Firma electronica de prescripciones con ECDSA P-256 / SHA-256 (FIPS 186-5).

Es firma electronica en los terminos de la Ley 25.506: la clave la custodia
el sistema, no un certificador licenciado. El paso a firma digital reemplaza
este modulo por la firma con el certificado X.509 del medico.
"""

import base64
import hashlib
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)

ALGORITMO = "ECDSA-P256-SHA256"


def generar_par_claves() -> tuple[str, str]:
    """Genera un par de claves P-256 y devuelve (privada_pem, publica_pem)."""
    try:
        privada = ec.generate_private_key(ec.SECP256R1())
        privada_pem = privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        publica_pem = (
            privada.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )
        return privada_pem, publica_pem
    except Exception as exc:
        logger.error("Error al generar el par de claves de firma: %s", type(exc).__name__)
        raise


def huella_clave_publica(publica_pem: str) -> str:
    """Devuelve el SHA-256 en hexadecimal de la clave publica en formato DER."""
    try:
        publica = serialization.load_pem_public_key(publica_pem.encode("ascii"))
        der = publica.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(der).hexdigest()
    except Exception as exc:
        logger.error("Error al calcular la huella de la clave publica: %s", type(exc).__name__)
        raise


def firmar(privada_pem: str, contenido: str) -> str:
    """Firma el contenido (texto UTF-8) y devuelve la firma DER en base64."""
    try:
        privada = serialization.load_pem_private_key(privada_pem.encode("ascii"), password=None)
        firma = privada.sign(contenido.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(firma).decode("ascii")
    except Exception as exc:
        logger.error("Error al firmar el contenido: %s", type(exc).__name__)
        raise


def verificar(publica_pem: str, contenido: str, firma_b64: str) -> bool:
    """Verifica una firma ECDSA P-256. Devuelve False si no corresponde al contenido."""
    try:
        publica = serialization.load_pem_public_key(publica_pem.encode("ascii"))
        publica.verify(base64.b64decode(firma_b64), contenido.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
    except Exception as exc:
        logger.warning("Firma no verificable: %s", type(exc).__name__)
        return False
