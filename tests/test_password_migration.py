"""Argon2id y migracion transparente desde el formato legacy SHA-256+salt."""

import hashlib

from backend.security.password import hash_password, needs_rehash, verify_password


def test_hash_y_verificacion_argon2():
    stored, salt = hash_password("clave-segura-123")
    assert salt == "argon2"
    assert stored.startswith("$argon2id$")
    assert verify_password("clave-segura-123", stored, salt)
    assert not verify_password("clave-incorrecta", stored, salt)


def test_verificacion_legacy_sha256():
    salt = "abc123"
    stored = hashlib.sha256((salt + "vieja-clave").encode()).hexdigest()
    assert verify_password("vieja-clave", stored, salt)
    assert not verify_password("otra-clave", stored, salt)


def test_needs_rehash_solo_para_legacy():
    salt = "abc123"
    legacy = hashlib.sha256((salt + "clave").encode()).hexdigest()
    assert needs_rehash(legacy, salt)

    stored, argon_salt = hash_password("clave")
    assert not needs_rehash(stored, argon_salt)


def test_hashes_distintos_para_misma_clave():
    """Argon2 usa salt propio embebido: dos hashes de la misma clave difieren."""
    h1, _ = hash_password("misma-clave")
    h2, _ = hash_password("misma-clave")
    assert h1 != h2
    assert verify_password("misma-clave", h1, "argon2")
    assert verify_password("misma-clave", h2, "argon2")
