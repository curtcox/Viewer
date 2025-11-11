"""Generic CRUD operations for user-scoped entities.

This module provides a generic repository pattern for entities that share common
attributes (user_id, name, template) to eliminate duplication across entity types.
"""

from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Query

# TypeVar for generic entity type
T = TypeVar('T')


class GenericEntityRepository(Generic[T]):
    """Generic repository for user-scoped entities with common CRUD operations.

    This class provides standard database operations for entities that have:
    - user_id: str (for user scoping)
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

    def get_all_for_user(self, user_id: str) -> List[T]:
        """Get all entities for a user, ordered by name.

        Args:
            user_id: User identifier

        Returns:
            List of entities ordered alphabetically by name
        """
        return self.model.query.filter_by(user_id=user_id).order_by(self.model.name).all()

    def get_templates_for_user(self, user_id: str) -> List[T]:
        """Get template entities for a user, ordered by name.

        Args:
            user_id: User identifier

        Returns:
            List of template entities ordered alphabetically by name
        """
        return (
            self.model.query.filter_by(user_id=user_id, template=True)
            .order_by(self.model.name)
            .all()
        )

    def get_by_name(self, user_id: str, name: str) -> Optional[T]:
        """Get entity by name for a user.

        Args:
            user_id: User identifier
            name: Entity name

        Returns:
            Entity if found, None otherwise
        """
        return self.model.query.filter_by(user_id=user_id, name=name).first()

    def get_first_name(self, user_id: str, exclude_name: Optional[str] = None) -> Optional[str]:
        """Get the first entity name for a user, ordered alphabetically.

        Args:
            user_id: User identifier
            exclude_name: Optional name to exclude from results

        Returns:
            First entity name if any exist, None otherwise
        """
        query = self.model.query.filter_by(user_id=user_id)

        # Optionally exclude a specific name (useful for finding alternatives)
        if exclude_name:
            query = query.filter(self.model.name != exclude_name)

        entity = query.order_by(self.model.name.asc()).first()
        return entity.name if entity else None

    def count_for_user(self, user_id: str) -> int:
        """Count entities for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of entities owned by the user
        """
        return self.model.query.filter_by(user_id=user_id).count()

    def get_all(self) -> List[T]:
        """Get all entities across all users (admin operation).

        Returns:
            List of all entities
        """
        return self.model.query.all()

    def count_all(self) -> int:
        """Count all entities across all users (admin operation).

        Returns:
            Total number of entities
        """
        return self.model.query.count()

    def exists(self, user_id: str, name: str) -> bool:
        """Check if an entity with given name exists for a user.

        Args:
            user_id: User identifier
            name: Entity name to check

        Returns:
            True if entity exists, False otherwise
        """
        return self.model.query.filter_by(user_id=user_id, name=name).count() > 0

    def _base_query(self) -> Query:
        """Get base query for the model (for subclass extension).

        Returns:
            SQLAlchemy query object
        """
        return self.model.query
