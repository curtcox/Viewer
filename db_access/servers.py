"""Server CRUD operations."""

from typing import List, Optional

from models import Server
from db_access._common import DEFAULT_AI_SERVER_NAME


def get_user_servers(user_id: str) -> List[Server]:
    """Return all servers for a user ordered by name."""
    return Server.query.filter_by(user_id=user_id).order_by(Server.name).all()


def get_user_template_servers(user_id: str) -> List[Server]:
    """Return template servers for a user ordered by name."""
    return (
        Server.query.filter_by(user_id=user_id, template=True)
        .order_by(Server.name)
        .all()
    )


def get_server_by_name(user_id: str, name: str) -> Optional[Server]:
    """Return a server by name for a user."""
    return Server.query.filter_by(user_id=user_id, name=name).first()


def get_first_server_name(user_id: str) -> Optional[str]:
    """Return the first server name for a user ordered alphabetically."""
    # Prefer user-created servers over the default AI helper when available.
    preferred = (
        Server.query.filter_by(user_id=user_id)
        .filter(Server.name != DEFAULT_AI_SERVER_NAME)
        .order_by(Server.name.asc())
        .first()
    )
    if preferred is not None:
        return preferred.name

    fallback = (
        Server.query.filter_by(user_id=user_id)
        .order_by(Server.name.asc())
        .first()
    )
    return fallback.name if fallback else None


def count_user_servers(user_id: str) -> int:
    """Return the count of servers for a user."""
    return Server.query.filter_by(user_id=user_id).count()


def get_all_servers() -> List[Server]:
    """Return all server records."""
    return Server.query.all()


def count_servers() -> int:
    """Return the total count of servers."""
    return Server.query.count()

