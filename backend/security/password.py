"""
Hashing de contrasenas con Argon2id.

Reemplaza SHA-256+salt por Argon2id (resistente a GPU/ASIC).
Soporta migracion transparente: si un hash existente es SHA-256,
lo verifica con el metodo legacy y re-hashea con Argon2id en el proximo login.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> tuple[str, str]:
    """Hashea una contrasena con Argon2id.

    Returns:
        Tuple de (hash_argon2, salt_placeholder).
        El salt esta embebido en el hash de Argon2 pero se retorna "argon2"
        como marcador para distinguir del formato legacy.
    """
    hashed = _hasher.hash(password)
    return hashed, "argon2"


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifica una contrasena contra el hash almacenado.

    Soporta ambos formatos:
    - Argon2id (salt == "argon2"): verificacion nativa.
    - SHA-256 legacy (salt != "argon2"): verificacion con SHA-256(salt+password).
    """
    if salt == "argon2":
        try:
            return _hasher.verify(stored_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
    else:
        legacy_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return secrets.compare_digest(legacy_hash, stored_hash)


def needs_rehash(stored_hash: str, salt: str) -> bool:
    """Indica si el hash debe ser actualizado (formato legacy o parametros desactualizados)."""
    if salt != "argon2":
        return True
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except Exception:
        return True
