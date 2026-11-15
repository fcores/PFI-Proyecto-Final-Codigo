"""
Modulo de cifrado de campos PHI — unico punto del codigo que toca primitivas criptograficas.

Implementa:
- AES-256-GCM con nonce aleatorio de 96 bits por operacion.
- AAD (Additional Authenticated Data) vinculando ciphertext al patient_id y al nombre del campo.
- Indice ciego HMAC-SHA256 para busqueda exacta sin descifrar.
- HKDF-SHA256 para derivar claves separadas (cifrado vs indice) desde una clave maestra unica.
- Formato versionado autodescriptivo: v1:<key_version>:<nonce_b64>:<ct_tag_b64>

La clave maestra NUNCA debe aparecer en logs, excepciones, repr ni respuestas.
"""

import base64
import hashlib
import hmac
import logging
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)

_NONCE_BYTES = 12  # 96 bits
_KEY_BYTES = 32  # 256 bits
_FORMAT_VERSION = "v1"

_INFO_ENCRYPTION = b"medchain/field-encryption"
_INFO_BLIND_INDEX = b"medchain/blind-index"


class CryptoService:
    """Servicio de cifrado de campos PHI con AES-256-GCM y indices ciegos HMAC."""

    def __init__(self, master_key: bytes, key_version: str = "v1") -> None:
        """
        Args:
            master_key: Clave maestra de 32 bytes (generada con os.urandom(32)).
            key_version: Version de la clave para el formato del ciphertext.
        """
        if len(master_key) != _KEY_BYTES:
            raise ValueError(f"La clave maestra debe ser de {_KEY_BYTES} bytes")
        self._key_version = key_version
        self._enc_key = self._derive_key(master_key, _INFO_ENCRYPTION)
        self._idx_key = self._derive_key(master_key, _INFO_BLIND_INDEX)

    def _derive_key(self, master: bytes, info: bytes) -> bytes:
        """Deriva una clave de proposito especifico con HKDF-SHA256."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=_KEY_BYTES,
            salt=None,
            info=info,
        )
        return hkdf.derive(master)

    def encrypt_field(self, plaintext: str, patient_id: int, field_name: str) -> str:
        """Cifra un campo de texto con AES-256-GCM.

        Args:
            plaintext: Valor en claro del campo.
            patient_id: ID del paciente (se usa como parte del AAD).
            field_name: Nombre del campo (se usa como parte del AAD).

        Returns:
            String con formato v1:<key_version>:<nonce_b64>:<ct_tag_b64>
        """
        nonce = os.urandom(_NONCE_BYTES)
        aad = f"patient:{patient_id}:{field_name}".encode()
        aesgcm = AESGCM(self._enc_key)
        ct_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)

        nonce_b64 = base64.b64encode(nonce).decode("ascii")
        ct_b64 = base64.b64encode(ct_and_tag).decode("ascii")

        return f"{_FORMAT_VERSION}:{self._key_version}:{nonce_b64}:{ct_b64}"

    def decrypt_field(self, ciphertext: str, patient_id: int, field_name: str) -> str:
        """Descifra un campo cifrado con AES-256-GCM.

        Args:
            ciphertext: Valor cifrado con formato v1:<key_version>:<nonce_b64>:<ct_tag_b64>
            patient_id: ID del paciente (debe coincidir con el AAD original).
            field_name: Nombre del campo (debe coincidir con el AAD original).

        Returns:
            Valor en claro.

        Raises:
            ValueError: Si el formato es invalido.
            cryptography.exceptions.InvalidTag: Si el AAD no coincide o el dato fue manipulado.
        """
        parts = ciphertext.split(":")
        if len(parts) != 4 or parts[0] != _FORMAT_VERSION:
            raise ValueError("Formato de ciphertext invalido")

        _version, key_ver, nonce_b64, ct_b64 = parts
        nonce = base64.b64decode(nonce_b64)
        ct_and_tag = base64.b64decode(ct_b64)
        aad = f"patient:{patient_id}:{field_name}".encode()

        aesgcm = AESGCM(self._enc_key)
        plaintext_bytes = aesgcm.decrypt(nonce, ct_and_tag, aad)
        return plaintext_bytes.decode("utf-8")

    def encrypt_secret(self, plaintext: str, context: str) -> str:
        """Cifra un secreto que no es PHI (p. ej. una clave privada de firma).

        El contexto viaja como AAD: un ciphertext copiado a otro registro no
        descifra.
        """
        try:
            nonce = os.urandom(_NONCE_BYTES)
            aesgcm = AESGCM(self._enc_key)
            ct_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), ("secret:" + context).encode("utf-8"))
            nonce_b64 = base64.b64encode(nonce).decode("ascii")
            ct_b64 = base64.b64encode(ct_and_tag).decode("ascii")
            return f"{_FORMAT_VERSION}:{self._key_version}:{nonce_b64}:{ct_b64}"
        except Exception as exc:
            logger.error("Error al cifrar un secreto: %s", type(exc).__name__)
            raise

    def decrypt_secret(self, ciphertext: str, context: str) -> str:
        """Descifra un secreto cifrado con encrypt_secret para el mismo contexto."""
        try:
            parts = ciphertext.split(":")
            if len(parts) != 4 or parts[0] != _FORMAT_VERSION:
                raise ValueError("Formato de ciphertext invalido")
            nonce = base64.b64decode(parts[2])
            ct_and_tag = base64.b64decode(parts[3])
            aesgcm = AESGCM(self._enc_key)
            plaintext_bytes = aesgcm.decrypt(nonce, ct_and_tag, ("secret:" + context).encode("utf-8"))
            return plaintext_bytes.decode("utf-8")
        except Exception as exc:
            logger.error("Error al descifrar un secreto: %s", type(exc).__name__)
            raise

    def blind_index(self, value: str) -> bytes:
        """Genera un indice ciego HMAC-SHA256 para busqueda exacta.

        El valor se normaliza (lowercase, stripped) antes del HMAC para que
        la busqueda sea case-insensitive.

        Args:
            value: Valor en claro a indexar.

        Returns:
            32 bytes del HMAC (persistir como BYTEA en la DB).
        """
        normalized = value.strip().lower()
        return hmac.new(self._idx_key, normalized.encode("utf-8"), hashlib.sha256).digest()

    def blind_index_token(self, token: str) -> bytes:
        """Genera un indice ciego para un token individual (una palabra).
        Util para buscar por palabras sueltas del nombre/apellido.
        """
        normalized = token.strip().lower()
        if not normalized:
            raise ValueError("Token vacio para indice ciego")
        return hmac.new(self._idx_key, normalized.encode("utf-8"), hashlib.sha256).digest()


def mask_value(value: str, visible_chars: int = 2) -> str:
    """Enmascara un valor dejando solo los primeros N caracteres visibles."""
    if not value or len(value) <= visible_chars:
        return "*" * max(len(value) if value else 0, 4)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)
