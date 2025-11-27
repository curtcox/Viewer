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
    count_aliases,
    get_alias_by_name,
    get_alias_by_target_path,
    get_aliases,
    get_first_alias_name,
    get_template_aliases,
    update_alias_cid_reference,
)
from .cids import (
    LiteralCIDRecord,
    count_cids,
    create_cid_record,
    find_cids_by_prefix,
    get_cid_by_path,
    get_cids_by_paths,
    get_first_cid,
    get_recent_cids,
    get_uploads,
    update_cid_references,
)
from .uploads import (
    get_template_uploads,
)
from .exports import (
    get_exports,
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
    get_server_invocations,
    get_server_invocations_by_result_cids,
    get_server_invocations_by_server,
)
from .page_views import (
    count_page_views,
    count_unique_page_view_paths,
    get_popular_page_paths,
    paginate_page_views,
    save_page_view,
)
from .secrets import (
    count_secrets,
    get_first_secret_name,
    get_secret_by_name,
    get_secrets,
    get_template_secrets,
)
from .servers import (
    count_servers,
    get_first_server_name,
    get_server_by_name,
    get_servers,
    get_template_servers,
)
from .variables import (
    count_variables,
    get_first_variable_name,
    get_template_variables,
    get_variable_by_name,
    get_variables,
)

EXPORTS: Dict[str, Any] = {
    # Common utilities
    "save_entity": save_entity,
    "delete_entity": delete_entity,
    "rollback_session": rollback_session,
    # Constants
    "DEFAULT_AI_SERVER_NAME": DEFAULT_AI_SERVER_NAME,
    "DEFAULT_AI_ALIAS_NAME": DEFAULT_AI_ALIAS_NAME,
    "DEFAULT_CSS_ALIAS_NAME": DEFAULT_CSS_ALIAS_NAME,
    "DEFAULT_ACTION": DEFAULT_ACTION,
    "MAX_MESSAGE_LENGTH": MAX_MESSAGE_LENGTH,
    # Servers
    "get_servers": get_servers,
    "get_template_servers": get_template_servers,
    "get_server_by_name": get_server_by_name,
    "get_first_server_name": get_first_server_name,
    "count_servers": count_servers,
    # Aliases
    "get_aliases": get_aliases,
    "get_template_aliases": get_template_aliases,
    "get_alias_by_name": get_alias_by_name,
    "get_first_alias_name": get_first_alias_name,
    "get_alias_by_target_path": get_alias_by_target_path,
    "count_aliases": count_aliases,
    "update_alias_cid_reference": update_alias_cid_reference,
    # Variables
    "get_variables": get_variables,
    "get_template_variables": get_template_variables,
    "get_variable_by_name": get_variable_by_name,
    "get_first_variable_name": get_first_variable_name,
    "count_variables": count_variables,
    # Secrets
    "get_secrets": get_secrets,
    "get_template_secrets": get_template_secrets,
    "get_secret_by_name": get_secret_by_name,
    "get_first_secret_name": get_first_secret_name,
    "count_secrets": count_secrets,
    # CIDs
    "LiteralCIDRecord": LiteralCIDRecord,
    "get_cid_by_path": get_cid_by_path,
    "find_cids_by_prefix": find_cids_by_prefix,
    "create_cid_record": create_cid_record,
    "get_uploads": get_uploads,
    "get_template_uploads": get_template_uploads,
    "get_cids_by_paths": get_cids_by_paths,
    "get_recent_cids": get_recent_cids,
    "get_first_cid": get_first_cid,
    "count_cids": count_cids,
    "update_cid_references": update_cid_references,
    # Page views
    "save_page_view": save_page_view,
    "count_page_views": count_page_views,
    "count_unique_page_view_paths": count_unique_page_view_paths,
    "get_popular_page_paths": get_popular_page_paths,
    "paginate_page_views": paginate_page_views,
    # Interactions
    "EntityInteractionRequest": EntityInteractionRequest,
    "EntityInteractionLookup": EntityInteractionLookup,
    "record_entity_interaction": record_entity_interaction,
    "get_recent_entity_interactions": get_recent_entity_interactions,
    "find_entity_interaction": find_entity_interaction,
    "get_entity_interactions": get_entity_interactions,
    # Invocations
    "ServerInvocationInput": ServerInvocationInput,
    "create_server_invocation": create_server_invocation,
    "get_server_invocations": get_server_invocations,
    "get_server_invocations_by_server": get_server_invocations_by_server,
    "get_server_invocations_by_result_cids": get_server_invocations_by_result_cids,
    "find_server_invocations_by_cid": find_server_invocations_by_cid,
    # Exports
    "record_export": record_export,
    "get_exports": get_exports,
}

__all__ = list(EXPORTS)

# Legacy alias constants maintained for backward compatibility.
_DEFAULT_AI_SERVER_NAME = DEFAULT_AI_SERVER_NAME
_DEFAULT_AI_ALIAS_NAME = DEFAULT_AI_ALIAS_NAME
_DEFAULT_CSS_ALIAS_NAME = DEFAULT_CSS_ALIAS_NAME

LEGACY_DEFAULTS: Dict[str, Any] = {
    "_DEFAULT_AI_SERVER_NAME": DEFAULT_AI_SERVER_NAME,
    "_DEFAULT_AI_ALIAS_NAME": DEFAULT_AI_ALIAS_NAME,
    "_DEFAULT_CSS_ALIAS_NAME": DEFAULT_CSS_ALIAS_NAME,
}
