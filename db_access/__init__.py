"""Database access functions organised by domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _exports
from ._exports import LEGACY_DEFAULTS

__all__ = list(_exports.__all__)
globals().update(_exports.EXPORTS)
globals().update(LEGACY_DEFAULTS)

if TYPE_CHECKING:  # pragma: no cover
    from ._exports import (  # pylint: disable=unused-import  # noqa: F401
        DEFAULT_ACTION,
        DEFAULT_AI_ALIAS_NAME,
        DEFAULT_AI_SERVER_NAME,
        DEFAULT_CSS_ALIAS_NAME,
        EntityInteractionLookup,
        EntityInteractionRequest,
        MAX_MESSAGE_LENGTH,
        ServerInvocationInput,
        count_cids,
        count_page_views,
        count_secrets,
        count_servers,
        count_unique_page_view_paths,
        count_variables,
        create_cid_record,
        create_server_invocation,
        delete_entity,
        find_cids_by_prefix,
        find_entity_interaction,
        find_server_invocations_by_cid,
        get_alias_by_name,
        get_alias_by_target_path,
        get_aliases,
        get_cid_by_path,
        get_cids_by_paths,
        get_entity_interactions,
        get_first_alias_name,
        get_first_cid,
        get_first_secret_name,
        get_first_server_name,
        get_first_variable_name,
        get_popular_page_paths,
        get_recent_cids,
        get_recent_entity_interactions,
        get_secret_by_name,
        get_secrets,
        get_server_by_name,
        get_server_invocations,
        get_server_invocations_by_result_cids,
        get_server_invocations_by_server,
        get_servers,
        get_template_aliases,
        get_template_secrets,
        get_template_servers,
        get_template_uploads,
        get_template_variables,
        get_uploads,
        get_variable_by_name,
        get_variables,
        paginate_page_views,
        record_entity_interaction,
        record_export,
        rollback_session,
        save_entity,
        save_page_view,
        update_alias_cid_reference,
        update_cid_references,
    )
