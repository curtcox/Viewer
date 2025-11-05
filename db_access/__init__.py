"""Database access functions organized by domain.

This package provides database access functions split into domain-specific modules:
- servers: Server CRUD operations
- aliases: Alias CRUD operations and CID reference management
- variables: Variable CRUD operations
- secrets: Secret CRUD operations
- cids: CID management operations
- page_views: Page view tracking and analytics
- interactions: Entity interaction tracking
- invocations: Server invocation tracking
- profile: User profile data operations
- _common: Shared utilities and constants

All functions are re-exported here for backward compatibility with existing code.
"""

# Import all functions and classes for backward compatibility
from db_access._common import (
    DEFAULT_AI_ALIAS_NAME,
    DEFAULT_AI_SERVER_NAME,
    DEFAULT_CSS_ALIAS_NAME,
    DEFAULT_ACTION,
    MAX_MESSAGE_LENGTH,
    delete_entity,
    rollback_session,
    save_entity,
)

from db_access.aliases import (
    count_user_aliases,
    get_alias_by_name,
    get_alias_by_target_path,
    get_first_alias_name,
    get_user_aliases,
    get_user_template_aliases,
    update_alias_cid_reference,
)

from db_access.cids import (
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

from db_access.interactions import (
    EntityInteractionLookup,
    EntityInteractionRequest,
    find_entity_interaction,
    get_entity_interactions,
    get_recent_entity_interactions,
    record_entity_interaction,
)

from db_access.invocations import (
    ServerInvocationInput,
    create_server_invocation,
    find_server_invocations_by_cid,
    get_user_server_invocations,
    get_user_server_invocations_by_result_cids,
    get_user_server_invocations_by_server,
)

from db_access.page_views import (
    count_page_views,
    count_unique_page_view_paths,
    count_user_page_views,
    get_popular_page_paths,
    paginate_user_page_views,
    save_page_view,
)

from db_access.profile import get_user_profile_data

from db_access.secrets import (
    count_secrets,
    count_user_secrets,
    get_first_secret_name,
    get_secret_by_name,
    get_user_secrets,
    get_user_template_secrets,
)

from db_access.servers import (
    count_servers,
    count_user_servers,
    get_all_servers,
    get_first_server_name,
    get_server_by_name,
    get_user_servers,
    get_user_template_servers,
)

from db_access.variables import (
    count_user_variables,
    count_variables,
    get_first_variable_name,
    get_variable_by_name,
    get_user_template_variables,
    get_user_variables,
)

from db_access.exports import (
    get_user_exports,
    record_export,
)

# Re-export constants that were previously module-level
_DEFAULT_AI_SERVER_NAME = DEFAULT_AI_SERVER_NAME
_DEFAULT_AI_ALIAS_NAME = DEFAULT_AI_ALIAS_NAME
_DEFAULT_CSS_ALIAS_NAME = DEFAULT_CSS_ALIAS_NAME

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

