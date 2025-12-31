"""Unit tests for the content_decoder module."""

import gzip
import zlib
from unittest.mock import MagicMock

import pytest

from server_utils.external_api.content_decoder import (
    auto_decode_response,
    decode_content,
)


class TestDecodeContent:
    """Tests for decode_content function."""

    def test_returns_bytes_unchanged_when_no_encoding(self) -> None:
        """Content without encoding should be returned as-is."""
        content = b"hello world"
        result = decode_content(content, None)
        assert result == content

    def test_returns_bytes_unchanged_when_empty_encoding(self) -> None:
        """Content with empty encoding string should be returned as-is."""
        content = b"hello world"
        result = decode_content(content, "")
        assert result == content

    def test_returns_bytes_unchanged_for_identity_encoding(self) -> None:
        """Identity encoding means no compression."""
        content = b"hello world"
        result = decode_content(content, "identity")
        assert result == content

    def test_returns_bytes_unchanged_for_none_encoding(self) -> None:
        """'none' encoding means no compression."""
        content = b"hello world"
        result = decode_content(content, "none")
        assert result == content

    def test_decompresses_gzip_content(self) -> None:
        """Gzip-encoded content should be decompressed."""
        original = b"hello world"
        compressed = gzip.compress(original)
        result = decode_content(compressed, "gzip")
        assert result == original

    def test_decompresses_deflate_content_with_zlib_header(self) -> None:
        """Deflate content with zlib header should be decompressed."""
        original = b"hello world"
        compressed = zlib.compress(original)
        result = decode_content(compressed, "deflate")
        assert result == original

    def test_decompresses_raw_deflate_content(self) -> None:
        """Raw deflate content (no zlib header) should be decompressed."""
        original = b"hello world"
        compress_obj = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -zlib.MAX_WBITS)
        compressed = compress_obj.compress(original) + compress_obj.flush()
        result = decode_content(compressed, "deflate")
        assert result == original

    def test_handles_stacked_encodings(self) -> None:
        """Multiple comma-separated encodings should be processed in reverse order."""
        original = b"hello world"
        # First gzip, then... identity (no-op)
        compressed = gzip.compress(original)
        result = decode_content(compressed, "identity, gzip")
        assert result == original

    def test_handles_encoding_with_whitespace(self) -> None:
        """Encoding values with leading/trailing whitespace should be normalized."""
        original = b"hello world"
        compressed = gzip.compress(original)
        result = decode_content(compressed, "  gzip  ")
        assert result == original

    def test_handles_string_content(self) -> None:
        """String content should be encoded to UTF-8 bytes."""
        content = "hello world"
        result = decode_content(content, None)  # type: ignore
        assert result == b"hello world"

    def test_handles_bytearray_content(self) -> None:
        """Bytearray content should be handled correctly."""
        original = b"hello world"
        compressed = bytearray(gzip.compress(original))
        result = decode_content(compressed, "gzip")
        assert result == original

    def test_brotli_raises_value_error_when_not_installed(self) -> None:
        """Brotli encoding should raise ValueError if brotli library is not installed."""
        # This test assumes brotli is not installed; if it is, the test will be skipped
        try:
            import brotli  # noqa: F401

            pytest.skip("brotli is installed, cannot test missing library case")
        except ImportError:
            pass

        with pytest.raises(ValueError, match="brotli library is not installed"):
            decode_content(b"compressed data", "br")

    def test_unknown_encoding_leaves_content_unchanged(self) -> None:
        """Unknown encodings should leave content unchanged (permissive behavior)."""
        content = b"hello world"
        result = decode_content(content, "unknown-encoding")
        assert result == content

    def test_handles_mixed_case_encoding(self) -> None:
        """Encoding names should be case-insensitive."""
        original = b"hello world"
        compressed = gzip.compress(original)
        result = decode_content(compressed, "GZIP")
        assert result == original


class TestAutoDecodeResponse:
    """Tests for auto_decode_response function."""

    def test_extracts_content_and_encoding_from_response(self) -> None:
        """Should extract content and Content-Encoding header from response."""
        original = b"hello world"
        compressed = gzip.compress(original)

        mock_response = MagicMock()
        mock_response.content = compressed
        mock_response.headers = {"Content-Encoding": "gzip"}

        result = auto_decode_response(mock_response)
        assert result == original

    def test_handles_response_without_encoding_header(self) -> None:
        """Should handle responses without Content-Encoding header."""
        content = b"hello world"

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.headers = {}

        result = auto_decode_response(mock_response)
        assert result == content

    def test_handles_response_with_none_encoding(self) -> None:
        """Should handle responses where Content-Encoding is None."""
        content = b"hello world"

        mock_response = MagicMock()
        mock_response.content = content
        mock_response.headers.get.return_value = None

        result = auto_decode_response(mock_response)
        assert result == content
