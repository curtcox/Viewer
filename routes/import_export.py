"""
DEPRECATED: This module has been decomposed into the import_export package.

This file now serves as a compatibility shim to redirect imports.
The actual implementation is in routes/import_export/*.py
"""
from __future__ import annotations

# Re-export the main route functions
from .import_export import export_data, export_size, import_data

# Re-export legacy import functions for backward compatibility
from .import_export.import_entities import (
    import_aliases as _import_aliases,
    import_servers as _import_servers,
    import_variables as _import_variables,
    import_secrets as _import_secrets,
    prepare_alias_import as _prepare_alias_import,
)

# Re-export internal functions used by tests
from .import_export.export_engine import build_export_payload as _build_export_payload
from .import_export.export_helpers import SELECTION_SENTINEL as _SELECTION_SENTINEL
from .import_export.cid_utils import (
    parse_cid_values_section as _parse_cid_values_section,
    store_cid_entry as _store_cid_entry,
)
from .import_export.import_sources import (
    parse_source_entry as _parse_source_entry,
    resolve_source_entry as _resolve_source_entry,
    load_source_entry_bytes as _load_source_entry_bytes,
    source_entry_matches_export as _source_entry_matches_export,
)
from .import_export.import_engine import (
    ImportContext as _ImportContext,
    SectionImportPlan as _SectionImportPlan,
    import_section as _import_section,
)
from .import_export.change_history import gather_change_history as _gather_change_history

# Re-export database access functions for test mocking
# These are imported from db_access in the sub-modules, but tests need to patch them here
from db_access import (
    get_user_aliases,
    get_user_servers,
    get_user_variables,
    get_user_secrets,
    get_user_uploads,
)
from cid_utils import store_cid_from_bytes
from cid_presenter import cid_path

__all__ = [
    'export_data',
    'export_size',
    'import_data',
    '_import_aliases',
    '_import_servers',
    '_import_variables',
    '_import_secrets',
    '_build_export_payload',
    '_SELECTION_SENTINEL',
    '_parse_cid_values_section',
    '_store_cid_entry',
    '_parse_source_entry',
    '_resolve_source_entry',
    '_load_source_entry_bytes',
    '_source_entry_matches_export',
    '_prepare_alias_import',
    '_ImportContext',
    '_SectionImportPlan',
    '_import_section',
    '_gather_change_history',
    'get_user_aliases',
    'get_user_servers',
    'get_user_variables',
    'get_user_secrets',
    'get_user_uploads',
    'store_cid_from_bytes',
    'cid_path',
]
