"""String normalization and manipulation utilities.

This module provides centralized string handling to eliminate scattered
.strip() calls and ensure consistent input normalization across the codebase.
"""

from typing import Optional


class StringNormalizer:
    """Normalize and sanitize string inputs consistently."""

    @staticmethod
    def normalize(value: Optional[str], *, default: str = "") -> str:
        """Normalize string by stripping whitespace and handling None.

        Args:
            value: Input string (can be None)
            default: Default value if input is None or empty after stripping

        Returns:
            Normalized string (stripped, never None)

        Examples:
            >>> StringNormalizer.normalize("  hello  ")
            "hello"
            >>> StringNormalizer.normalize(None)
            ""
            >>> StringNormalizer.normalize("", default="default")
            "default"
            >>> StringNormalizer.normalize("  ", default="default")
            "default"
        """
        normalized = (value or "").strip()
        return normalized if normalized else default

    @staticmethod
    def normalize_path(
        value: Optional[str], *, remove_leading_slash: bool = True
    ) -> str:
        """Normalize path string by stripping and optionally removing leading slash.

        Args:
            value: Input path string (can be None)
            remove_leading_slash: If True, remove leading '/' from path

        Returns:
            Normalized path string

        Examples:
            >>> StringNormalizer.normalize_path("  /foo/bar  ")
            "foo/bar"
            >>> StringNormalizer.normalize_path("/foo", remove_leading_slash=False)
            "/foo"
        """
        normalized = StringNormalizer.normalize(value)
        if remove_leading_slash and normalized.startswith("/"):
            normalized = normalized[1:].strip()
        return normalized

    @staticmethod
    def normalize_identifier(value: Optional[str]) -> str:
        """Normalize entity identifier (name, key, etc.) by stripping whitespace.

        This is specifically for entity names, variable names, etc. where
        we want to preserve the string but remove leading/trailing whitespace.

        Args:
            value: Input identifier string (can be None)

        Returns:
            Normalized identifier string (empty string if None)

        Examples:
            >>> StringNormalizer.normalize_identifier("  myVariable  ")
            "myVariable"
            >>> StringNormalizer.normalize_identifier(None)
            ""
        """
        return StringNormalizer.normalize(value)

    @staticmethod
    def normalize_multiline(value: Optional[str]) -> str:
        """Normalize multi-line text by stripping leading/trailing whitespace.

        Preserves internal structure but removes outer whitespace.

        Args:
            value: Input multi-line string (can be None)

        Returns:
            Normalized multi-line string

        Examples:
            >>> StringNormalizer.normalize_multiline("  line1\\n  line2  ")
            "line1\\n  line2"
        """
        return StringNormalizer.normalize(value)

    @staticmethod
    def safe_strip(value: Optional[str]) -> str:
        """Safely strip a string that may be None.

        This is a convenience method for the common pattern of (value or "").strip()

        Args:
            value: Input string (can be None)

        Returns:
            Stripped string (empty string if None)

        Examples:
            >>> StringNormalizer.safe_strip("  hello  ")
            "hello"
            >>> StringNormalizer.safe_strip(None)
            ""
        """
        return (value or "").strip()

    @staticmethod
    def normalize_with_fallback(
        primary: Optional[str], fallback: Optional[str] = None
    ) -> str:
        """Normalize string with fallback to another value if primary is empty.

        Args:
            primary: Primary value to use
            fallback: Fallback value if primary is empty

        Returns:
            Normalized primary or fallback value

        Examples:
            >>> StringNormalizer.normalize_with_fallback("  ", "backup")
            "backup"
            >>> StringNormalizer.normalize_with_fallback("primary", "backup")
            "primary"
        """
        normalized_primary = StringNormalizer.normalize(primary)
        if normalized_primary:
            return normalized_primary
        return StringNormalizer.normalize(fallback)


# Convenience functions for common use cases
def safe_strip(value: Optional[str]) -> str:
    """Convenience function for safely stripping strings.

    Args:
        value: String to strip (can be None)

    Returns:
        Stripped string (empty if None)
    """
    return StringNormalizer.safe_strip(value)


def normalize_name(value: Optional[str]) -> str:
    """Convenience function for normalizing entity names.

    Args:
        value: Name to normalize (can be None)

    Returns:
        Normalized name (empty if None)
    """
    return StringNormalizer.normalize_identifier(value)


def normalize_path(value: Optional[str], remove_leading_slash: bool = True) -> str:
    """Convenience function for normalizing paths.

    Args:
        value: Path to normalize (can be None)
        remove_leading_slash: Whether to remove leading slash

    Returns:
        Normalized path
    """
    return StringNormalizer.normalize_path(
        value, remove_leading_slash=remove_leading_slash
    )
