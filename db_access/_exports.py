"""Centralised export definitions for the :mod:`db_access` package."""

from __future__ import annotations

from typing import Any, Dict

from ._common import (
    DEFAULT_ACTION,
    DEFAULT_AI_ALIAS_NAME,
    DEFAULT_AI_SERVER_NAME,
    DEFAULT_CSS_ALIAS_NAME,
    MAX_MESSAGE_LENGTH,
    delete_entity,
    rollback_session,
    save_entity,
)
from .aliases import (
    count_user_aliases,
    get_alias_by_name,
    get_alias_by_target_path,
    get_first_alias_name,
    get_user_aliases,
    get_user_template_aliases,
    update_alias_cid_reference,
)
from .cids import (
    count_cids,
    create_cid_record,
    find_cids_by_prefix,
    get_cid_by_path,
    get_cids_by_paths,
    get_first_cid,
    get_recent_cids,
    get_user_uploads,
    update_cid_references,
)
from .exports import (
    get_user_exports,
    record_export,
)
from .interactions import (
    EntityInteractionLookup,
    EntityInteractionRequest,
    find_entity_interaction,
    get_entity_interactions,
    get_recent_entity_interactions,
    record_entity_interaction,
)
from .invocations import (
    ServerInvocationInput,
    create_server_invocation,
    find_server_invocations_by_cid,
    get_user_server_invocations,
    get_user_server_invocations_by_result_cids,
    get_user_server_invocations_by_server,
)
from .page_views import (
    count_page_views,
    count_unique_page_view_paths,
    count_user_page_views,
    get_popular_page_paths,
    paginate_user_page_views,
    save_page_view,
)
from .profile import get_user_profile_data
from .secrets import (
    count_secrets,
    count_user_secrets,
    get_first_secret_name,
    get_secret_by_name,
    get_user_secrets,
    get_user_template_secrets,
)
from .servers import (
    count_servers,
    count_user_servers,
    get_all_servers,
    get_first_server_name,
    get_server_by_name,
    get_user_servers,
    get_user_template_servers,
)
from .variables import (
    count_user_variables,
    count_variables,
    get_first_variable_name,
    get_user_template_variables,
    get_user_variables,
    get_variable_by_name,
)

__all__ = [
    # Common utilities
    "save_entity",
    "delete_entity",
    "rollback_session",
    # Constants
    "DEFAULT_AI_SERVER_NAME",
    "DEFAULT_AI_ALIAS_NAME",
    "DEFAULT_CSS_ALIAS_NAME",
    "DEFAULT_ACTION",
    "MAX_MESSAGE_LENGTH",
    # Servers
    "get_user_servers",
    "get_user_template_servers",
    "get_server_by_name",
    "get_first_server_name",
    "count_user_servers",
    "get_all_servers",
    "count_servers",
    # Aliases
    "get_user_aliases",
    "get_user_template_aliases",
    "get_alias_by_name",
    "get_first_alias_name",
    "get_alias_by_target_path",
    "count_user_aliases",
    "update_alias_cid_reference",
    # Variables
    "get_user_variables",
    "get_user_template_variables",
    "get_variable_by_name",
    "get_first_variable_name",
    "count_user_variables",
    "count_variables",
    # Secrets
    "get_user_secrets",
    "get_user_template_secrets",
    "get_secret_by_name",
    "get_first_secret_name",
    "count_user_secrets",
    "count_secrets",
    # CIDs
    "get_cid_by_path",
    "find_cids_by_prefix",
    "create_cid_record",
    "get_user_uploads",
    "get_cids_by_paths",
    "get_recent_cids",
    "get_first_cid",
    "count_cids",
    "update_cid_references",
    # Page views
    "save_page_view",
    "count_user_page_views",
    "count_unique_page_view_paths",
    "get_popular_page_paths",
    "paginate_user_page_views",
    "count_page_views",
    # Interactions
    "EntityInteractionRequest",
    "EntityInteractionLookup",
    "record_entity_interaction",
    "get_recent_entity_interactions",
    "find_entity_interaction",
    "get_entity_interactions",
    # Invocations
    "ServerInvocationInput",
    "create_server_invocation",
    "get_user_server_invocations",
    "get_user_server_invocations_by_server",
    "get_user_server_invocations_by_result_cids",
    "find_server_invocations_by_cid",
    # Exports
    "record_export",
    "get_user_exports",
    # Profile
    "get_user_profile_data",
]

# Legacy alias constants maintained for backward compatibility.
_DEFAULT_AI_SERVER_NAME = DEFAULT_AI_SERVER_NAME
_DEFAULT_AI_ALIAS_NAME = DEFAULT_AI_ALIAS_NAME
_DEFAULT_CSS_ALIAS_NAME = DEFAULT_CSS_ALIAS_NAME

LEGACY_DEFAULTS: Dict[str, Any] = {
    "_DEFAULT_AI_SERVER_NAME": DEFAULT_AI_SERVER_NAME,
    "_DEFAULT_AI_ALIAS_NAME": DEFAULT_AI_ALIAS_NAME,
    "_DEFAULT_CSS_ALIAS_NAME": DEFAULT_CSS_ALIAS_NAME,
}


def _collect_exports() -> Dict[str, Any]:
    """Return a mapping of public attribute names to exportable objects."""

    return {name: globals()[name] for name in __all__}


EXPORTS: Dict[str, Any] = _collect_exports()
