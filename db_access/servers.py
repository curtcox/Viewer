"""Server CRUD operations."""

from typing import List, Optional

from models import Server
from db_access._common import DEFAULT_AI_SERVER_NAME
from db_access.generic_crud import GenericEntityRepository

# Create repository instance for Server entities
_server_repo = GenericEntityRepository(Server)


def get_servers() -> List[Server]:
    """Return all servers ordered by name."""
    return _server_repo.get_all()


def get_template_servers() -> List[Server]:
    """Return template servers from templates variable configuration."""
    from template_manager import get_templates_for_type, ENTITY_TYPE_SERVERS, resolve_cid_value

    templates = get_templates_for_type(ENTITY_TYPE_SERVERS)

    # Convert template dicts to Server objects (read-only representations)
    server_objects = []
    for template in templates:
        # Create a minimal Server object from template data
        server = Server()
        # Templates are not persisted DB rows, so id remains None
        server.id = None
        # Store the template key in a separate attribute for UI use
        server.template_key = template.get('key', '')
        server.name = template.get('name', template.get('key', ''))

        # Try to get definition from various possible fields
        definition = template.get('definition')
        if not definition and template.get('definition_cid'):
            definition = resolve_cid_value(template.get('definition_cid'))

        server.definition = definition or ''
        server.enabled = True
        server.template = True  # Mark as template for backwards compatibility
        server_objects.append(server)

    return sorted(server_objects, key=lambda s: s.name if s.name else '')


def get_server_by_name(name: str) -> Optional[Server]:
    """Return a server by name."""
    return _server_repo.get_by_name(name)


def get_first_server_name() -> Optional[str]:
    """Return the first server name ordered alphabetically.

    Prefers user-created servers over the default AI helper when available.
    """
    # Try to get first server excluding the default AI server
    preferred = _server_repo.get_first_name(exclude_name=DEFAULT_AI_SERVER_NAME)
    if preferred is not None:
        return preferred

    # Fallback to any server (including default AI server)
    return _server_repo.get_first_name()


def count_servers() -> int:
    """Return the count of servers."""
    return _server_repo.count()
