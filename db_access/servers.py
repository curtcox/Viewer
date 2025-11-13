"""Server CRUD operations."""

from typing import List, Optional

from models import Server
from db_access._common import DEFAULT_AI_SERVER_NAME
from db_access.generic_crud import GenericEntityRepository

# Create repository instance for Server entities
_server_repo = GenericEntityRepository(Server)


def get_user_servers(user_id: str) -> List[Server]:
    """Return all servers for a user ordered by name."""
    return _server_repo.get_all_for_user(user_id)


def get_user_template_servers(user_id: str) -> List[Server]:
    """Return template servers from templates variable configuration."""
    from template_manager import get_templates_for_type, ENTITY_TYPE_SERVERS, resolve_cid_value

    templates = get_templates_for_type(user_id, ENTITY_TYPE_SERVERS)

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
        server.user_id = user_id

        # Try to get definition from various possible fields
        definition = template.get('definition')
        if not definition and template.get('definition_cid'):
            definition = resolve_cid_value(template.get('definition_cid'))

        server.definition = definition or ''
        server.enabled = True
        server.template = True  # Mark as template for backwards compatibility
        server_objects.append(server)

    return sorted(server_objects, key=lambda s: s.name if s.name else '')


def get_server_by_name(user_id: str, name: str) -> Optional[Server]:
    """Return a server by name for a user."""
    return _server_repo.get_by_name(user_id, name)


def get_first_server_name(user_id: str) -> Optional[str]:
    """Return the first server name for a user ordered alphabetically.

    Prefers user-created servers over the default AI helper when available.
    """
    # Try to get first server excluding the default AI server
    preferred = _server_repo.get_first_name(user_id, exclude_name=DEFAULT_AI_SERVER_NAME)
    if preferred is not None:
        return preferred

    # Fallback to any server (including default AI server)
    return _server_repo.get_first_name(user_id)


def count_user_servers(user_id: str) -> int:
    """Return the count of servers for a user."""
    return _server_repo.count_for_user(user_id)


def get_all_servers() -> List[Server]:
    """Return all server records."""
    return _server_repo.get_all()


def count_servers() -> int:
    """Return the total count of servers."""
    return _server_repo.count_all()
