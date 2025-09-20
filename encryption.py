"""Utility helpers for encrypting and decrypting secret values."""
from __future__ import annotations

import base64
import os
from hashlib import sha256
from hmac import compare_digest, new as hmac_new

_SECRET_IV_SIZE = 16
_SECRET_MAC_SIZE = 32
SECRET_ENCRYPTION_SCHEME = "xor-hmac-sha256"


def _derive_keystream(key_material: bytes, iv: bytes, length: int) -> bytes:
    """Derive a pseudo-random keystream using repeated SHA-256 hashing.

    The keystream is deterministic for a given key and IV so the same
    parameters can decrypt previously encrypted values.
    """
    if length <= 0:
        return b""

    stream = bytearray()
    counter = 0
    while len(stream) < length:
        counter_bytes = counter.to_bytes(4, "big", signed=False)
        digest = sha256(key_material + iv + counter_bytes).digest()
        stream.extend(digest)
        counter += 1
    return bytes(stream[:length])


def encrypt_secret_value(plaintext: str, key: str) -> str:
    """Encrypt a plaintext secret using the provided key.

    Args:
        plaintext: The secret value to encrypt.
        key: A user-supplied passphrase.

    Returns:
        A base64-url encoded ciphertext that includes the IV and HMAC for
        authentication.

    Raises:
        ValueError: If the key is empty.
    """
    if not key:
        raise ValueError("Encryption key is required")

    key_material = sha256(key.encode("utf-8")).digest()
    iv = os.urandom(_SECRET_IV_SIZE)
    data = plaintext.encode("utf-8")
    keystream = _derive_keystream(key_material, iv, len(data))
    ciphertext = bytes(a ^ b for a, b in zip(data, keystream))
    mac = hmac_new(key_material, iv + ciphertext, sha256).digest()
    payload = iv + ciphertext + mac
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decrypt_secret_value(ciphertext_token: str, key: str) -> str:
    """Decrypt a ciphertext produced by :func:`encrypt_secret_value`.

    Args:
        ciphertext_token: The encoded ciphertext returned from encryption.
        key: The user-supplied passphrase.

    Returns:
        The decrypted plaintext string.

    Raises:
        ValueError: If the token is malformed or the key is incorrect.
    """
    if not key:
        raise ValueError("Decryption key is required")

    try:
        raw = base64.urlsafe_b64decode(ciphertext_token.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - base64 handles specifics
        raise ValueError("Invalid encrypted secret payload") from exc

    if len(raw) < _SECRET_IV_SIZE + _SECRET_MAC_SIZE:
        raise ValueError("Invalid encrypted secret payload")

    iv = raw[:_SECRET_IV_SIZE]
    mac = raw[-_SECRET_MAC_SIZE:]
    ciphertext = raw[_SECRET_IV_SIZE:-_SECRET_MAC_SIZE]

    key_material = sha256(key.encode("utf-8")).digest()
    expected_mac = hmac_new(key_material, iv + ciphertext, sha256).digest()
    if not compare_digest(mac, expected_mac):
        raise ValueError("Invalid encryption key")

    keystream = _derive_keystream(key_material, iv, len(ciphertext))
    plaintext_bytes = bytes(a ^ b for a, b in zip(ciphertext, keystream))
    try:
        return plaintext_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError("Invalid encrypted secret payload") from exc


__all__ = [
    "SECRET_ENCRYPTION_SCHEME",
    "decrypt_secret_value",
    "encrypt_secret_value",
]
