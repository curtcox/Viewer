"""Core CID (Content Identifier) functionality.

This module provides the fundamental building blocks for Content Identifiers (CIDs),
including generation, parsing, validation, and format specification.

CID Format:
-----------
A CID consists of two parts:
1. Length prefix (8 characters): Base64url-encoded content length (6 bytes)
2. Payload (variable length):
   - For content <= 64 bytes: Base64url-encoded content itself (direct embed)
   - For content > 64 bytes: Base64url-encoded SHA-512 digest (86 characters)

Example CID: AAAAAAAA (empty content, length 0)
Example CID: AAAABGFiY2Q (4 bytes of direct content: "abcd")
"""

import base64
import binascii
import hashlib
import re
from typing import Optional, Tuple


# ============================================================================
# CID FORMAT CONSTANTS
# ============================================================================

# Character class allowed in CID strings
CID_CHARACTER_CLASS = "A-Za-z0-9_-"

# Length prefix encoding
CID_LENGTH_PREFIX_BYTES = 6  # 6 bytes = 48 bits for content length
CID_LENGTH_PREFIX_CHARS = 8  # 6 bytes encoded in base64url = 8 characters

# SHA-512 digest size
SHA512_DIGEST_SIZE = hashlib.sha512().digest_size  # 64 bytes
CID_SHA512_CHARS = 86  # 64 bytes encoded in base64url = 86 characters

# Total CID length for hashed content
CID_LENGTH = CID_LENGTH_PREFIX_CHARS + CID_SHA512_CHARS  # 94 characters

# Minimum CID length (just the length prefix)
CID_MIN_LENGTH = CID_LENGTH_PREFIX_CHARS

# Minimum length for a CID reference (shorter prefixes allowed for lookups)
CID_MIN_REFERENCE_LENGTH = 6

# Strict minimum length (same as min length for validation)
CID_STRICT_MIN_LENGTH = CID_MIN_LENGTH

# Maximum content length that can be encoded
MAX_CONTENT_LENGTH = (1 << (CID_LENGTH_PREFIX_BYTES * 8)) - 1

# Direct content embed limit (content <= this size is embedded directly)
DIRECT_CONTENT_EMBED_LIMIT = 64


# ============================================================================
# CID VALIDATION PATTERNS
# ============================================================================

# Pattern for normalized CIDs (full format)
CID_NORMALIZED_PATTERN = re.compile(
    rf"^[{CID_CHARACTER_CLASS}]{{{CID_MIN_LENGTH},{CID_LENGTH}}}$"
)

# Pattern for CID references (allows shorter prefixes)
CID_REFERENCE_PATTERN = re.compile(
    rf"^[{CID_CHARACTER_CLASS}]{{{CID_MIN_REFERENCE_LENGTH},}}$"
)

# Strict pattern for validation
CID_STRICT_PATTERN = re.compile(
    rf"^[{CID_CHARACTER_CLASS}]{{{CID_STRICT_MIN_LENGTH},}}$"
)

# Pattern for extracting CID from path (with optional extension)
CID_PATH_CAPTURE_PATTERN = re.compile(
    rf"/([{CID_CHARACTER_CLASS}]{{{CID_MIN_REFERENCE_LENGTH},}})(?:\.[A-Za-z0-9]+)?"
)


# ============================================================================
# BASE64URL ENCODING HELPERS
# ============================================================================


def base64url_encode(data: bytes) -> str:
    """Encode bytes as URL-safe base64 without padding.

    Args:
        data: Bytes to encode

    Returns:
        URL-safe base64 string without padding characters

    Example:
        >>> base64url_encode(b"hello")
        'aGVsbG8'
    """
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def base64url_decode(data: str) -> bytes:
    """Decode URL-safe base64 data that may omit padding.

    Args:
        data: Base64url string (padding optional)

    Returns:
        Decoded bytes

    Raises:
        binascii.Error: If data contains invalid base64 characters

    Example:
        >>> base64url_decode('aGVsbG8')
        b'hello'
    """
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


# ============================================================================
# CID COMPONENT NORMALIZATION
# ============================================================================


def normalize_component(value: Optional[str]) -> str:
    """Normalize a CID component by removing whitespace and leading slashes.

    Args:
        value: String to normalize (may be None)

    Returns:
        Normalized string, or empty string if invalid

    Example:
        >>> normalize_component("  /abc123  ")
        'abc123'
        >>> normalize_component("abc/def")  # Slashes in middle not allowed
        ''
    """
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    normalized = normalized.lstrip("/")
    if "/" in normalized:
        return ""
    return normalized


# ============================================================================
# CID VALIDATION FUNCTIONS
# ============================================================================


def is_probable_cid_component(value: Optional[str]) -> bool:
    """Check if a value could be a CID or CID prefix.

    Args:
        value: String to check

    Returns:
        True if value matches CID character requirements

    Example:
        >>> is_probable_cid_component("AAAAAAAA")
        True
        >>> is_probable_cid_component("abc.txt")
        False
    """
    normalized = normalize_component(value)
    if not normalized or "." in normalized:
        return False
    return bool(CID_REFERENCE_PATTERN.fullmatch(normalized))


def is_strict_cid_candidate(value: Optional[str]) -> bool:
    """Check if a value is a strong candidate for a generated CID.

    Args:
        value: String to check

    Returns:
        True if value matches strict CID format

    Example:
        >>> is_strict_cid_candidate("AAAAAAAA")
        True
        >>> is_strict_cid_candidate("short")
        False
    """
    normalized = normalize_component(value)
    if not normalized or "." in normalized:
        return False
    return bool(CID_STRICT_PATTERN.fullmatch(normalized))


def is_normalized_cid(value: Optional[str]) -> bool:
    """Check if a value is exactly formatted like a generated CID.

    This performs full validation including parsing the CID structure.

    Args:
        value: String to check

    Returns:
        True if value is a valid, properly formatted CID

    Example:
        >>> is_normalized_cid("AAAAAAAA")
        True
        >>> is_normalized_cid("invalid")
        False
    """
    normalized = normalize_component(value)
    if not normalized or "." in normalized:
        return False
    if not CID_NORMALIZED_PATTERN.fullmatch(normalized):
        return False
    try:
        parse_cid_components(normalized)
    except ValueError:
        return False
    return True


def split_cid_path(value: Optional[str]) -> Optional[Tuple[str, Optional[str]]]:
    """Extract CID value and optional extension from a path.

    Args:
        value: Path string (e.g., "/CID.ext?query#anchor")

    Returns:
        Tuple of (cid, extension) or None if path doesn't contain a valid CID
        Extension may be None if no extension present

    Example:
        >>> split_cid_path("/AAAAAAAA.txt")
        ('AAAAAAAA', 'txt')
        >>> split_cid_path("/AAAAAAAA")
        ('AAAAAAAA', None)
        >>> split_cid_path("/invalid/path")
        None
    """
    if value is None:
        return None

    slug = value.strip()
    if not slug:
        return None

    # Remove query and anchor
    slug = slug.split("?", 1)[0]
    slug = slug.split("#", 1)[0]
    if not slug:
        return None

    # Remove leading slash
    if slug.startswith("/"):
        slug = slug[1:]

    # Reject paths with slashes in the middle
    if not slug or "/" in slug:
        return None

    # Split CID and extension
    cid_part = slug
    extension: Optional[str] = None
    if "." in slug:
        cid_part, extension = slug.split(".", 1)
        extension = extension or None

    if not is_probable_cid_component(cid_part):
        return None

    return cid_part, extension


# ============================================================================
# CID GENERATION AND PARSING
# ============================================================================


def encode_cid_length(length: int) -> str:
    """Encode the content length into the CID prefix.

    Args:
        length: Content length in bytes (0 to MAX_CONTENT_LENGTH)

    Returns:
        8-character base64url-encoded length prefix

    Raises:
        ValueError: If length is out of valid range

    Example:
        >>> encode_cid_length(0)
        'AAAAAAAA'
        >>> encode_cid_length(42)
        'AAAAACo'
    """
    if length < 0 or length > MAX_CONTENT_LENGTH:
        raise ValueError(
            f"CID content length must be between 0 and {MAX_CONTENT_LENGTH} bytes"
        )

    encoded = base64url_encode(length.to_bytes(CID_LENGTH_PREFIX_BYTES, "big"))
    if len(encoded) != CID_LENGTH_PREFIX_CHARS:
        raise ValueError("Encoded length prefix must be 8 characters long")
    return encoded


def parse_cid_components(cid: str) -> Tuple[int, bytes]:
    """Parse a CID into its content length and payload.

    For CIDs with content <= DIRECT_CONTENT_EMBED_LIMIT bytes, the payload
    is the original content. For larger content, the payload is the SHA-512 digest.

    Args:
        cid: Base64url-encoded CID string

    Returns:
        Tuple of (content_length, payload_bytes)

    Raises:
        ValueError: If CID format is invalid, malformed, or not canonical

    Example:
        >>> length, data = parse_cid_components("AAAAAAAA")
        >>> length
        0
        >>> data
        b''
    """
    normalized = normalize_component(cid)
    if len(normalized) < CID_MIN_LENGTH:
        raise ValueError("CID is missing the length prefix")
    if not CID_NORMALIZED_PATTERN.fullmatch(normalized):
        raise ValueError("CID contains invalid characters")

    length_part = normalized[:CID_LENGTH_PREFIX_CHARS]
    payload_part = normalized[CID_LENGTH_PREFIX_CHARS:]

    # Decode length prefix
    try:
        length_bytes = base64url_decode(length_part)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("CID contains invalid base64 encoding") from exc

    if len(length_bytes) != CID_LENGTH_PREFIX_BYTES:
        raise ValueError("CID length prefix has an unexpected size")

    content_length = int.from_bytes(length_bytes, "big")

    # Handle direct content embedding
    if content_length <= DIRECT_CONTENT_EMBED_LIMIT:
        try:
            payload_bytes = base64url_decode(payload_part)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("CID content payload is not valid base64") from exc

        if len(payload_bytes) != content_length:
            raise ValueError("CID embedded content length mismatch")
        if base64url_encode(payload_bytes) != payload_part:
            raise ValueError("CID embedded content is not in canonical form")
        return content_length, payload_bytes

    # Handle hashed content
    if len(payload_part) != CID_SHA512_CHARS:
        raise ValueError("CID digest must be 86 characters long")

    try:
        digest_bytes = base64url_decode(payload_part)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("CID digest payload is not valid base64") from exc

    if len(digest_bytes) != SHA512_DIGEST_SIZE:
        raise ValueError("CID digest has an unexpected size")
    if base64url_encode(digest_bytes) != payload_part:
        raise ValueError("CID digest is not in canonical form")

    return content_length, digest_bytes


def generate_cid(file_data: bytes) -> str:
    """Generate a CID for the given content.

    The CID format consists of a length prefix followed by either:
    - Direct content embedding (for content <= 64 bytes)
    - SHA-512 digest (for content > 64 bytes)

    Args:
        file_data: Content to generate CID for

    Returns:
        Complete CID string

    Raises:
        ValueError: If content exceeds maximum size or digest encoding fails

    Example:
        >>> generate_cid(b"")
        'AAAAAAAA'
        >>> generate_cid(b"hello")
        'AAAABWhlbGxv'
    """
    content_length = len(file_data)
    length_part = encode_cid_length(content_length)

    # Direct content embedding for small content
    if content_length <= DIRECT_CONTENT_EMBED_LIMIT:
        content_part = base64url_encode(file_data)
        return f"{length_part}{content_part}"

    # Hash-based CID for larger content
    digest = hashlib.sha512(file_data).digest()
    digest_part = base64url_encode(digest)

    if len(digest_part) != CID_SHA512_CHARS:
        raise ValueError("SHA-512 digest must encode to 86 characters")

    return f"{length_part}{digest_part}"


def is_literal_cid(cid: str) -> bool:
    """Check if a CID contains literal (directly embedded) content.

    A CID is literal if its content length is <= DIRECT_CONTENT_EMBED_LIMIT (64 bytes),
    meaning the content is embedded directly in the CID rather than being a hash.

    Args:
        cid: CID string to check (may include leading slash)

    Returns:
        True if the CID contains literal content, False otherwise

    Example:
        >>> is_literal_cid("AAAAAAAA")  # Empty content
        True
        >>> is_literal_cid("AAAABWhlbGxv")  # "hello" embedded
        True
        >>> is_literal_cid("/AAAABWhlbGxv")  # Works with leading slash
        True
    """
    normalized = normalize_component(cid)
    if not normalized:
        return False

    try:
        content_length, _ = parse_cid_components(normalized)
        return content_length <= DIRECT_CONTENT_EMBED_LIMIT
    except ValueError:
        return False


def extract_literal_content(cid: str) -> Optional[bytes]:
    """Extract the literal content from a CID if it contains embedded content.

    This function extracts content directly from CIDs that have content
    <= DIRECT_CONTENT_EMBED_LIMIT (64 bytes). For hash-based CIDs,
    returns None since the content cannot be derived from the hash.

    Args:
        cid: CID string (may include leading slash)

    Returns:
        The literal content bytes if the CID contains embedded content,
        None if the CID is hash-based or invalid

    Example:
        >>> extract_literal_content("AAAAAAAA")
        b''
        >>> extract_literal_content("AAAABWhlbGxv")
        b'hello'
        >>> extract_literal_content("/AAAABWhlbGxv")  # Works with leading slash
        b'hello'
    """
    normalized = normalize_component(cid)
    if not normalized:
        return None

    try:
        content_length, payload = parse_cid_components(normalized)
        if content_length <= DIRECT_CONTENT_EMBED_LIMIT:
            return payload
        return None
    except ValueError:
        return None
