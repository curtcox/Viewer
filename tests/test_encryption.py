"""Coverage-oriented tests for the encryption helpers."""

import base64
from hashlib import sha256
from hmac import new as hmac_new

import pytest

from encryption import (
    _derive_keystream,
    decrypt_secret_value,
    encrypt_secret_value,
)


def test_encrypt_handles_empty_plaintext_roundtrip():
    token = encrypt_secret_value("", "key")
    assert isinstance(token, str)
    assert decrypt_secret_value(token, "key") == ""


def test_encrypt_requires_non_empty_key():
    with pytest.raises(ValueError):
        encrypt_secret_value("secret", "")


def test_decrypt_requires_non_empty_key():
    token = encrypt_secret_value("secret", "key")
    with pytest.raises(ValueError):
        decrypt_secret_value(token, "")


def test_decrypt_rejects_incorrect_key():
    token = encrypt_secret_value("secret", "correct")
    with pytest.raises(ValueError):
        decrypt_secret_value(token, "incorrect")


def test_decrypt_surfaces_invalid_payload_encoding():
    key = "encoding-key"
    key_material = sha256(key.encode("utf-8")).digest()
    iv = bytes(range(16))

    # Choose plaintext bytes that are not valid UTF-8 so the decode step fails
    plaintext_bytes = b"\xff"
    keystream = _derive_keystream(key_material, iv, len(plaintext_bytes))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext_bytes, keystream))
    mac = hmac_new(key_material, iv + ciphertext, sha256).digest()

    payload = iv + ciphertext + mac
    token = base64.urlsafe_b64encode(payload).decode("utf-8")

    with pytest.raises(ValueError):
        decrypt_secret_value(token, key)


def test_decrypt_rejects_truncated_payload():
    with pytest.raises(ValueError):
        decrypt_secret_value(base64.urlsafe_b64encode(b"short").decode("utf-8"), "key")
