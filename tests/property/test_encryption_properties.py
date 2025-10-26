import base64

import pytest
from hypothesis import given, strategies as st

from encryption import decrypt_secret_value, encrypt_secret_value


@given(plaintext=st.text(), key=st.text(min_size=1))
def test_encrypt_decrypt_round_trip(plaintext: str, key: str) -> None:
    token = encrypt_secret_value(plaintext, key)
    assert decrypt_secret_value(token, key) == plaintext


def _mutated_token(plaintext: str, key: str, offset: int) -> tuple[str, str]:
    token = encrypt_secret_value(plaintext, key)
    payload = bytearray(base64.urlsafe_b64decode(token.encode("utf-8")))
    index = offset % len(payload)
    payload[index] ^= 0x01
    mutated_token = base64.urlsafe_b64encode(bytes(payload)).decode("utf-8")
    return mutated_token, key


@given(
    st.builds(
        _mutated_token,
        plaintext=st.text(),
        key=st.text(min_size=1),
        offset=st.integers(min_value=0, max_value=2**16),
    )
)
def test_decrypt_rejects_modified_payload(mutated_token_with_key: tuple[str, str]) -> None:
    mutated_token, key = mutated_token_with_key
    with pytest.raises(ValueError):
        decrypt_secret_value(mutated_token, key)
