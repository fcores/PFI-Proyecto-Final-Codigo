"""Tests obligatorios de la capa criptografica (R3.8 del plan)."""

import os

import pytest

from backend.security.crypto import CryptoService, mask_value


@pytest.fixture
def crypto():
    """CryptoService con clave de test generada aleatoriamente."""
    key = os.urandom(32)
    return CryptoService(master_key=key, key_version="test1")


@pytest.fixture
def crypto_v2():
    """Segundo CryptoService con clave diferente para tests de version."""
    key = os.urandom(32)
    return CryptoService(master_key=key, key_version="test2")


class TestEncryptDecryptRoundTrip:
    """Ida y vuelta: encrypt -> decrypt debe retornar el valor original."""

    def test_basic_roundtrip(self, crypto):
        plaintext = "Juan Carlos"
        ct = crypto.encrypt_field(plaintext, patient_id=42, field_name="first_name")
        result = crypto.decrypt_field(ct, patient_id=42, field_name="first_name")
        assert result == plaintext

    def test_empty_string(self, crypto):
        ct = crypto.encrypt_field("", patient_id=1, field_name="treatment")
        assert crypto.decrypt_field(ct, patient_id=1, field_name="treatment") == ""

    def test_unicode(self, crypto):
        plaintext = "María José Ñoño — diagnóstico: cáncer de colon"
        ct = crypto.encrypt_field(plaintext, patient_id=99, field_name="treatment")
        assert crypto.decrypt_field(ct, patient_id=99, field_name="treatment") == plaintext

    def test_format_version_prefix(self, crypto):
        ct = crypto.encrypt_field("test", patient_id=1, field_name="f")
        assert ct.startswith("v1:test1:")


class TestTamperDetection:
    """Alterar un byte del ciphertext o del AAD debe fallar la autenticacion."""

    def test_altered_ciphertext(self, crypto):
        ct = crypto.encrypt_field("secret", patient_id=1, field_name="first_name")
        parts = ct.split(":")
        import base64

        ct_bytes = bytearray(base64.b64decode(parts[3]))
        ct_bytes[0] ^= 0xFF  # Flip a byte
        parts[3] = base64.b64encode(bytes(ct_bytes)).decode()
        tampered = ":".join(parts)
        with pytest.raises(Exception):
            crypto.decrypt_field(tampered, patient_id=1, field_name="first_name")

    def test_wrong_patient_id(self, crypto):
        ct = crypto.encrypt_field("secret", patient_id=1, field_name="first_name")
        with pytest.raises(Exception):
            crypto.decrypt_field(ct, patient_id=2, field_name="first_name")

    def test_wrong_field_name(self, crypto):
        ct = crypto.encrypt_field("secret", patient_id=1, field_name="first_name")
        with pytest.raises(Exception):
            crypto.decrypt_field(ct, patient_id=1, field_name="last_name")


class TestNonceUniqueness:
    """Cada cifrado debe producir un ciphertext diferente (nonce unico)."""

    def test_same_input_different_output(self, crypto):
        ct1 = crypto.encrypt_field("same", patient_id=1, field_name="f")
        ct2 = crypto.encrypt_field("same", patient_id=1, field_name="f")
        assert ct1 != ct2  # Nonces diferentes


class TestBlindIndex:
    """El indice ciego debe ser deterministico y case-insensitive."""

    def test_deterministic(self, crypto):
        idx1 = crypto.blind_index("Pérez")
        idx2 = crypto.blind_index("Pérez")
        assert idx1 == idx2

    def test_case_insensitive(self, crypto):
        idx1 = crypto.blind_index("PEREZ")
        idx2 = crypto.blind_index("perez")
        assert idx1 == idx2

    def test_different_values_different_index(self, crypto):
        idx1 = crypto.blind_index("perez")
        idx2 = crypto.blind_index("gomez")
        assert idx1 != idx2

    def test_index_is_32_bytes(self, crypto):
        idx = crypto.blind_index("test")
        assert len(idx) == 32


class TestKeyVersionCompatibility:
    """Cifrado con una clave no debe descifrarse con otra."""

    def test_different_key_fails(self, crypto, crypto_v2):
        ct = crypto.encrypt_field("secret", patient_id=1, field_name="f")
        with pytest.raises(Exception):
            crypto_v2.decrypt_field(ct, patient_id=1, field_name="f")


class TestKeyValidation:
    """La clave debe ser exactamente 32 bytes."""

    def test_short_key_rejected(self):
        with pytest.raises(ValueError):
            CryptoService(master_key=os.urandom(16), key_version="bad")

    def test_long_key_rejected(self):
        with pytest.raises(ValueError):
            CryptoService(master_key=os.urandom(64), key_version="bad")


class TestMasking:
    """Enmascaramiento de valores."""

    def test_mask_normal(self):
        assert mask_value("Gonzalez", 2) == "Go******"

    def test_mask_short(self):
        result = mask_value("AB", 2)
        assert "*" in result

    def test_mask_empty(self):
        result = mask_value("", 2)
        assert result == "****"
