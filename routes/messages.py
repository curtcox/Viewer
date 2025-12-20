"""Standardized flash messages for entity operations.

This module provides consistent messaging across all entity CRUD operations,
reducing duplication and ensuring uniform user experience.
"""


class EntityMessages:
    """Standard flash messages for entity operations."""

    @staticmethod
    def created(entity_type: str, name: str) -> str:
        """Generate a success message for entity creation.

        Args:
            entity_type: Type of entity ('server', 'variable', 'secret', 'alias')
            name: Name of the created entity

        Returns:
            Formatted success message

        Example:
            >>> EntityMessages.created('server', 'api')
            'Server "api" created successfully!'
        """
        return f'{entity_type.title()} "{name}" created successfully!'

    @staticmethod
    def updated(entity_type: str, name: str) -> str:
        """Generate a success message for entity update.

        Args:
            entity_type: Type of entity ('server', 'variable', 'secret', 'alias')
            name: Name of the updated entity

        Returns:
            Formatted success message

        Example:
            >>> EntityMessages.updated('variable', 'API_KEY')
            'Variable "API_KEY" updated successfully!'
        """
        return f'{entity_type.title()} "{name}" updated successfully!'

    @staticmethod
    def deleted(entity_type: str, name: str) -> str:
        """Generate a success message for entity deletion.

        Args:
            entity_type: Type of entity ('server', 'variable', 'secret', 'alias')
            name: Name of the deleted entity

        Returns:
            Formatted success message

        Example:
            >>> EntityMessages.deleted('secret', 'PASSWORD')
            'Secret "PASSWORD" deleted successfully!'
        """
        return f'{entity_type.title()} "{name}" deleted successfully!'

    @staticmethod
    def already_exists(entity_type: str, name: str) -> str:
        """Generate an error message when entity already exists.

        Args:
            entity_type: Type of entity ('server', 'variable', 'secret', 'alias')
            name: Name of the existing entity

        Returns:
            Formatted error message

        Example:
            >>> EntityMessages.already_exists('alias', 'home')
            'An Alias named "home" already exists.'
        """
        # Use 'An' for vowel sounds, 'A' otherwise
        article = "An" if entity_type[0].lower() in "aeiou" else "A"
        return f'{article} {entity_type.title()} named "{name}" already exists.'

    @staticmethod
    def not_found(entity_type: str, name: str) -> str:
        """Generate an error message when entity is not found.

        Args:
            entity_type: Type of entity ('server', 'variable', 'secret', 'alias')
            name: Name of the missing entity

        Returns:
            Formatted error message

        Example:
            >>> EntityMessages.not_found('server', 'missing')
            'Server "missing" not found.'
        """
        return f'{entity_type.title()} "{name}" not found.'

    @staticmethod
    def bulk_updated(entity_type: str, count: int) -> str:
        """Generate a success message for bulk updates.

        Args:
            entity_type: Type of entity (plural: 'servers', 'variables', etc.)
            count: Number of entities updated

        Returns:
            Formatted success message

        Example:
            >>> EntityMessages.bulk_updated('variables', 5)
            'Variables updated successfully! (5 items)'
        """
        return f"{entity_type.title()} updated successfully! ({count} items)"
