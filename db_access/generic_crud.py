"""Generic CRUD operations for entities.

This module provides a generic repository pattern for entities that share common
attributes (name, template) to eliminate duplication across entity types.
"""

from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Query

# TypeVar for generic entity type
T = TypeVar("T")


class GenericEntityRepository(Generic[T]):
    """Generic repository for entities with common CRUD operations.

    This class provides standard database operations for entities that have:
    - name: str (for entity identification)
    - template: bool (optional, for template entities)

    Args:
        model_class: The SQLAlchemy model class (Server, Variable, Secret, etc.)
    """

    def __init__(self, model_class: Type[T]):
        """Initialize repository with a model class.

        Args:
            model_class: SQLAlchemy model class to operate on
        """
        self.model = model_class

    def get_all(self) -> List[T]:
        """Get all entities, ordered by name.

        Returns:
            List of entities ordered alphabetically by name
        """
        return self.model.query.order_by(self.model.name).all()

    def get_templates(self) -> List[T]:
        """Get template entities, ordered by name.

        Returns:
            List of template entities ordered alphabetically by name
        """
        return self.model.query.filter_by(template=True).order_by(self.model.name).all()

    def get_by_name(self, name: str) -> Optional[T]:
        """Get entity by name.

        Args:
            name: Entity name

        Returns:
            Entity if found, None otherwise
        """
        return self.model.query.filter_by(name=name).first()

    def get_first_name(self, exclude_name: Optional[str] = None) -> Optional[str]:
        """Get the first entity name, ordered alphabetically.

        Args:
            exclude_name: Optional name to exclude from results

        Returns:
            First entity name if any exist, None otherwise
        """
        query = self.model.query

        # Optionally exclude a specific name (useful for finding alternatives)
        if exclude_name:
            query = query.filter(self.model.name != exclude_name)

        entity = query.order_by(self.model.name.asc()).first()
        return entity.name if entity else None

    def count(self) -> int:
        """Count entities.

        Returns:
            Number of entities
        """
        return self.model.query.count()

    def exists(self, name: str) -> bool:
        """Check if an entity with given name exists.

        Args:
            name: Entity name to check

        Returns:
            True if entity exists, False otherwise
        """
        return self.model.query.filter_by(name=name).count() > 0

    def _base_query(self) -> Query:
        """Get base query for the model (for subclass extension).

        Returns:
            SQLAlchemy query object
        """
        return self.model.query
