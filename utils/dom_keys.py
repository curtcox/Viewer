"""DOM key generation utilities for creating stable element identifiers."""

import hashlib
import re
from typing import Optional


class DomKeyGenerator:
    """Generate stable DOM identifiers for entities and relationships."""

    @staticmethod
    def _make_id(prefix: str, value: Optional[str]) -> str:
        """
        Generate a stable DOM identifier combining a slug and hash suffix.

        Args:
            prefix: The prefix for the identifier (e.g., 'alias', 'server', 'ref')
            value: The value to generate an identifier for

        Returns:
            A stable DOM identifier string
        """
        text = (value or "").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        digest_source = text or prefix
        digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:8]
        if slug:
            return f"{prefix}-{slug}-{digest}"
        return f"{prefix}-{digest}"

    @staticmethod
    def entity_key(entity_type: str, identifier: Optional[str]) -> str:
        """
        Generate a unique DOM key for the given entity.

        Args:
            entity_type: The type of entity (e.g., 'alias', 'server', 'cid')
            identifier: The unique identifier for the entity

        Returns:
            A unique DOM key for the entity
        """
        return DomKeyGenerator._make_id(entity_type, identifier or entity_type)

    @staticmethod
    def reference_key(source_key: str, target_key: str) -> str:
        """
        Generate a DOM key representing a directed relationship between entities.

        Args:
            source_key: The DOM key of the source entity
            target_key: The DOM key of the target entity

        Returns:
            A DOM key representing the relationship
        """
        return DomKeyGenerator._make_id("ref", f"{source_key}->{target_key}")


# Backward compatibility functions
def _make_dom_id(prefix: str, value: Optional[str]) -> str:
    """Return a stable DOM identifier combining a slug and hash suffix."""
    return DomKeyGenerator._make_id(prefix, value)


def _entity_key(entity_type: str, identifier: Optional[str]) -> str:
    """Return a unique DOM key for the given entity descriptor."""
    return DomKeyGenerator.entity_key(entity_type, identifier)


def _reference_key(source_key: str, target_key: str) -> str:
    """Return a DOM key representing a directed relationship."""
    return DomKeyGenerator.reference_key(source_key, target_key)
