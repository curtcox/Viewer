"""Content decoder for HTTP responses with compressed content.

This module centralizes the logic for decompressing HTTP response bodies
that may be gzip, deflate, or brotli encoded. Use this when accessing
response.content directly instead of response.json() or response.text.
"""

import gzip
import zlib
from typing import Optional, Union


def decode_content(
    content: Union[bytes, bytearray, str],
    content_encoding: Optional[str],
) -> bytes:
    """
    Decode HTTP response content based on Content-Encoding header.

    Args:
        content: Raw response body (bytes, bytearray, or string)
        content_encoding: Value of Content-Encoding header (may be comma-separated)

    Returns:
        Decoded bytes

    Raises:
        ValueError: If brotli encoding is used but brotli library is not installed
        zlib.error: If deflate decompression fails
        gzip.BadGzipFile: If gzip decompression fails
    """
    # Normalize content to bytes
    if not isinstance(content, (bytes, bytearray)):
        return str(content).encode("utf-8")

    body = bytes(content)

    # No encoding means content is already decoded
    if not content_encoding:
        return body

    # Parse encoding header (may be comma-separated for stacked encodings)
    encodings = [
        encoding.strip().lower()
        for encoding in str(content_encoding).split(",")
        if encoding and str(encoding).strip()
    ]

    if not encodings:
        return body

    # Process encodings in reverse order (last applied = first to remove)
    for encoding in reversed(encodings):
        if encoding in {"identity", "none"}:
            continue

        if encoding == "gzip":
            body = gzip.decompress(body)
            continue

        if encoding == "deflate":
            try:
                body = zlib.decompress(body)
            except zlib.error:
                # Try raw deflate (no zlib header)
                body = zlib.decompress(body, -zlib.MAX_WBITS)
            continue

        if encoding == "br":
            try:
                import brotli  # type: ignore
            except ImportError as exc:
                raise ValueError(
                    "Response was brotli-compressed (Content-Encoding: br), "
                    "but the brotli library is not installed. "
                    "Install it with: pip install brotli"
                ) from exc
            body = brotli.decompress(body)
            continue

        # Unknown encoding - leave content as-is
        # (could also raise an error, but this is more permissive)

    return body


def auto_decode_response(response) -> bytes:
    """
    Extract and decode content from a requests.Response object.

    This is a convenience function that combines extracting the response
    content and Content-Encoding header, then calling decode_content().

    Args:
        response: A requests.Response object

    Returns:
        Decoded response body as bytes
    """
    content = response.content
    content_encoding = response.headers.get("Content-Encoding")
    return decode_content(content, content_encoding)
