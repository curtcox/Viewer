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
    """Return template servers for a user ordered by name."""
    return _server_repo.get_templates_for_user(user_id)


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
