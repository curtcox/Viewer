"""CID (Content Identifier) class with validation.

This module provides a strongly-typed CID class that ensures CIDs are always valid
through constructor validation. This eliminates the possibility of invalid CID strings
being passed around the application.

Usage:
    # Create from validated string
    cid = CID("AAAAAAAA")

    # Generate from content
    cid = CID.from_bytes(b"hello world")

    # Access underlying string
    print(cid.value)  # "AAAAAAAA"
    str(cid)          # "AAAAAAAA"

    # Check if content is embedded
    if cid.is_literal:
        content = cid.extract_literal_content()
"""

from typing import Optional
from cid_core import (
    generate_cid,
    is_normalized_cid,
    normalize_component,
    parse_cid_components,
    DIRECT_CONTENT_EMBED_LIMIT,
)


class CID:
    """A validated Content Identifier (CID).

    This class ensures that only valid CIDs can be created. Once constructed,
    the CID instance is immutable and guaranteed to contain a valid CID string.

    Attributes:
        value: The normalized CID string (without leading slashes)

    Raises:
        ValueError: If the provided string is not a valid CID
        TypeError: If the provided value is not a string

    Examples:
        >>> cid = CID("AAAAAAAA")  # Empty content
        >>> cid.value
        'AAAAAAAA'

        >>> cid = CID.from_bytes(b"hello")
        >>> cid.value
        'AAAAAAAFaGVsbG8'

        >>> cid = CID("invalid")  # Raises ValueError
        Traceback (most recent call last):
        ...
        ValueError: Invalid CID: 'invalid' is not a valid CID format
    """

    __slots__ = ("_value", "_content_length", "_payload")

    def __init__(self, cid_string: str):
        """Initialize a CID from a string.

        Args:
            cid_string: A CID string (with or without leading slash)

        Raises:
            ValueError: If cid_string is not a valid CID
            TypeError: If cid_string is not a string
        """
        if not isinstance(cid_string, str):
            raise TypeError(
                f"CID must be initialized with a string, got {type(cid_string).__name__}"
            )

        # Normalize and validate
        normalized = normalize_component(cid_string)
        if not normalized:
            raise ValueError(f"Invalid CID: '{cid_string}' normalizes to empty string")

        if not is_normalized_cid(normalized):
            raise ValueError(f"Invalid CID: '{cid_string}' is not a valid CID format")

        # Parse components to cache them
        try:
            content_length, payload = parse_cid_components(normalized)
        except ValueError as e:
            raise ValueError(
                f"Invalid CID: '{cid_string}' failed validation: {e}"
            ) from e

        # Store validated value and parsed components
        self._value = normalized
        self._content_length = content_length
        self._payload = payload

    @classmethod
    def from_bytes(cls, content: bytes) -> "CID":
        """Generate a CID from content bytes.

        Args:
            content: The content to generate a CID for

        Returns:
            A new CID instance

        Raises:
            ValueError: If content exceeds maximum size

        Examples:
            >>> cid = CID.from_bytes(b"")
            >>> cid.value
            'AAAAAAAA'

            >>> cid = CID.from_bytes(b"hello")
            >>> cid.value
            'AAAAAAAFaGVsbG8'
        """
        cid_string = generate_cid(content)
        return cls(cid_string)

    @classmethod
    def try_from_string(cls, cid_string: Optional[str]) -> Optional["CID"]:
        """Try to create a CID from a string, returning None if invalid.

        Args:
            cid_string: A potential CID string

        Returns:
            A CID instance if valid, None otherwise

        Examples:
            >>> CID.try_from_string("AAAAAAAA")
            CID('AAAAAAAA')

            >>> CID.try_from_string("invalid")
            None

            >>> CID.try_from_string(None)
            None
        """
        if cid_string is None:
            return None
        try:
            return cls(cid_string)
        except (ValueError, TypeError):
            return None

    @property
    def value(self) -> str:
        """Get the normalized CID string.

        Returns:
            The CID string without leading slashes
        """
        return self._value

    @property
    def content_length(self) -> int:
        """Get the content length encoded in the CID.

        Returns:
            The length of the original content in bytes
        """
        return self._content_length

    @property
    def is_literal(self) -> bool:
        """Check if this CID contains literal (embedded) content.

        Returns:
            True if content is embedded directly in the CID (≤64 bytes),
            False if the CID contains a hash of larger content
        """
        return self._content_length <= DIRECT_CONTENT_EMBED_LIMIT

    @property
    def payload(self) -> bytes:
        """Get the payload bytes (either embedded content or hash digest).

        Returns:
            For literal CIDs: the original content
            For hash-based CIDs: the SHA-512 digest
        """
        return self._payload

    def extract_literal_content(self) -> Optional[bytes]:
        """Extract embedded content if this is a literal CID.

        Returns:
            The embedded content bytes if this is a literal CID,
            None if this is a hash-based CID

        Examples:
            >>> cid = CID("AAAAAAAA")
            >>> cid.extract_literal_content()
            b''

            >>> cid = CID.from_bytes(b"hello")
            >>> cid.extract_literal_content()
            b'hello'
        """
        if self.is_literal:
            return self._payload
        return None

    def to_path(self, extension: Optional[str] = None) -> str:
        """Convert CID to a path format with leading slash.

        Args:
            extension: Optional file extension (without dot)

        Returns:
            Path string with leading slash and optional extension

        Examples:
            >>> cid = CID("AAAAAAAA")
            >>> cid.to_path()
            '/AAAAAAAA'

            >>> cid.to_path("txt")
            '/AAAAAAAA.txt'
        """
        if extension:
            return f"/{self._value}.{extension}"
        return f"/{self._value}"

    def __str__(self) -> str:
        """Convert to string (returns the CID value).

        Returns:
            The normalized CID string
        """
        return self._value

    def __repr__(self) -> str:
        """Get a developer-friendly representation.

        Returns:
            A string like "CID('AAAAAAAA')"
        """
        return f"CID('{self._value}')"

    def __eq__(self, other) -> bool:
        """Check equality with another CID or string.

        Args:
            other: Another CID instance or a string

        Returns:
            True if the CID values are equal

        Examples:
            >>> CID("AAAAAAAA") == CID("AAAAAAAA")
            True

            >>> CID("AAAAAAAA") == "AAAAAAAA"
            True

            >>> CID("AAAAAAAA") == CID("AAAAAAAFaGVsbG8")
            False
        """
        if isinstance(other, CID):
            return self._value == other._value
        if isinstance(other, str):
            # Compare with normalized version of the string
            try:
                other_normalized = normalize_component(other)
                return self._value == other_normalized
            except Exception:
                return False
        return False

    def __hash__(self) -> int:
        """Get hash for use in sets and dicts.

        Returns:
            Hash of the CID value
        """
        return hash(self._value)

    def __len__(self) -> int:
        """Get the length of the CID string.

        Returns:
            Length of the CID string in characters
        """
        return len(self._value)


# ============================================================================
# HELPER FUNCTIONS FOR INTEGRATION
# ============================================================================


def ensure_cid(value) -> "CID":
    """Convert a value to a CID, validating it if it's a string.

    This helper function makes it easy to write functions that accept
    either CID objects or strings and ensure they get a CID object.

    Args:
        value: A CID object or a CID string

    Returns:
        A CID object

    Raises:
        ValueError: If value is a string but not a valid CID
        TypeError: If value is neither a CID nor a string

    Examples:
        >>> cid = ensure_cid("AAAAAAAA")
        >>> isinstance(cid, CID)
        True

        >>> cid_obj = CID("AAAAAAAA")
        >>> ensure_cid(cid_obj) is cid_obj
        True
    """
    if isinstance(value, CID):
        return value
    if isinstance(value, str):
        return CID(value)
    raise TypeError(f"Expected CID or string, got {type(value).__name__}")


def to_cid_string(value) -> str:
    """Convert a CID object or string to a normalized CID string.

    Args:
        value: A CID object or a CID string

    Returns:
        Normalized CID string

    Raises:
        ValueError: If value is a string but not a valid CID
        TypeError: If value is neither a CID nor a string

    Examples:
        >>> to_cid_string(CID("AAAAAAAA"))
        'AAAAAAAA'

        >>> to_cid_string("AAAAAAAA")
        'AAAAAAAA'

        >>> to_cid_string("/AAAAAAAA")
        'AAAAAAAA'
    """
    if isinstance(value, CID):
        return value.value
    if isinstance(value, str):
        return CID(value).value
    raise TypeError(f"Expected CID or string, got {type(value).__name__}")
