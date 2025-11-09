"""Import/export package for handling user data exports and imports."""
from __future__ import annotations

# Import the main blueprint from the parent routes module
# This avoids circular imports while allowing routes.py access to main_bp
def __getattr__(name: str):
    """Lazy import to avoid circular dependencies and for backward compatibility."""
    if name == 'main_bp':
        from .. import main_bp
        return main_bp

    # Backward compatibility: internal functions used by tests
    if name == '_build_export_payload':
        from .export_engine import build_export_payload
        return build_export_payload
    if name == '_SELECTION_SENTINEL':
        from .export_helpers import SELECTION_SENTINEL
        return SELECTION_SENTINEL
    if name == '_parse_cid_values_section':
        from .cid_utils import parse_cid_values_section
        return parse_cid_values_section
    if name == '_store_cid_entry':
        from .cid_utils import store_cid_entry
        return store_cid_entry
    if name == '_parse_source_entry':
        from .import_sources import parse_source_entry
        return parse_source_entry
    if name == '_resolve_source_entry':
        from .import_sources import resolve_source_entry
        return resolve_source_entry
    if name == '_load_source_entry_bytes':
        from .import_sources import load_source_entry_bytes
        return load_source_entry_bytes
    if name == '_source_entry_matches_export':
        from .import_sources import source_entry_matches_export
        return source_entry_matches_export
    if name == '_import_aliases':
        from .import_entities import import_aliases
        return import_aliases
    if name == '_import_servers':
        from .import_entities import import_servers
        return import_servers
    if name == '_import_variables':
        from .import_entities import import_variables
        return import_variables
    if name == '_import_secrets':
        from .import_entities import import_secrets
        return import_secrets
    if name == '_prepare_alias_import':
        from .import_entities import prepare_alias_import
        return prepare_alias_import
    if name == '_ImportContext':
        from .import_engine import ImportContext
        return ImportContext
    if name == '_SectionImportPlan':
        from .import_engine import SectionImportPlan
        return SectionImportPlan
    if name == '_import_section':
        from .import_engine import import_section
        return import_section
    if name == '_process_import_submission':
        from .import_engine import process_import_submission
        return process_import_submission
    if name == '_gather_change_history':
        from .change_history import gather_change_history
        return gather_change_history
    if name == '_load_import_payload':
        from .import_sources import load_import_payload
        return load_import_payload

    # Database access functions for test mocking
    if name == 'get_user_aliases':
        from db_access import get_user_aliases
        return get_user_aliases
    if name == 'get_user_servers':
        from db_access import get_user_servers
        return get_user_servers
    if name == 'get_user_variables':
        from db_access import get_user_variables
        return get_user_variables
    if name == 'get_user_secrets':
        from db_access import get_user_secrets
        return get_user_secrets
    if name == 'get_user_uploads':
        from db_access import get_user_uploads
        return get_user_uploads
    if name == 'store_cid_from_bytes':
        from cid_utils import store_cid_from_bytes
        return store_cid_from_bytes
    if name == 'cid_path':
        from cid_presenter import cid_path
        return cid_path
    if name == 'current_user':
        from identity import current_user
        return current_user

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Re-export the route functions
# pylint: disable=wrong-import-position  # Must come after __getattr__ definition for lazy imports
from .routes import export_data, export_size, import_data  # noqa: E402

__all__ = ['export_data', 'export_size', 'import_data']
