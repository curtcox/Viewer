"""Import/export package for handling user data exports and imports.

This module uses lazy imports (__getattr__) for three purposes:
1. Breaking circular dependencies with the parent routes module
2. Maintaining backward compatibility with existing tests
3. Allowing tests to mock database access functions

For new code, prefer importing directly from submodules rather than
relying on this compatibility layer.
"""
from __future__ import annotations
from typing import Any
import importlib

# === LAZY IMPORT CONFIGURATION ===
# Dictionary-based lookup for cleaner, more maintainable lazy imports
# Format: 'attribute_name': ('module_path', 'attribute_in_module')

# Backward compatibility: internal functions used by tests
_LAZY_IMPORTS_INTERNAL = {
    '_build_export_payload': ('.export_engine', 'build_export_payload'),
    '_SELECTION_SENTINEL': ('.export_helpers', 'SELECTION_SENTINEL'),
    '_parse_cid_values_section': ('.cid_utils', 'parse_cid_values_section'),
    '_store_cid_entry': ('.cid_utils', 'store_cid_entry'),
    '_parse_source_entry': ('.import_sources', 'parse_source_entry'),
    '_resolve_source_entry': ('.import_sources', 'resolve_source_entry'),
    '_load_source_entry_bytes': ('.import_sources', 'load_source_entry_bytes'),
    '_source_entry_matches_export': ('.import_sources', 'source_entry_matches_export'),
    '_import_aliases': ('.import_entities', 'import_aliases'),
    '_import_servers': ('.import_entities', 'import_servers'),
    '_import_variables': ('.import_entities', 'import_variables'),
    '_import_secrets': ('.import_entities', 'import_secrets'),
    '_prepare_alias_import': ('.import_entities', 'prepare_alias_import'),
    '_ImportContext': ('.import_engine', 'ImportContext'),
    '_SectionImportPlan': ('.import_engine', 'SectionImportPlan'),
    '_import_section': ('.import_engine', 'import_section'),
    '_process_import_submission': ('.import_engine', 'process_import_submission'),
    '_gather_change_history': ('.change_history', 'gather_change_history'),
    '_load_import_payload': ('.import_sources', 'load_import_payload'),
}

# Database access functions for test mocking
_LAZY_IMPORTS_DATABASE = {
    'get_user_aliases': ('db_access', 'get_user_aliases'),
    'get_user_servers': ('db_access', 'get_user_servers'),
    'get_user_variables': ('db_access', 'get_user_variables'),
    'get_user_secrets': ('db_access', 'get_user_secrets'),
    'get_user_uploads': ('db_access', 'get_user_uploads'),
    'store_cid_from_bytes': ('cid_utils', 'store_cid_from_bytes'),
    'cid_path': ('cid_presenter', 'cid_path'),
    'current_user': ('identity', 'current_user'),
}


def __getattr__(name: str) -> Any:
    """Lazy import to avoid circular dependencies and for backward compatibility.

    Args:
        name: The name of the attribute to import

    Returns:
        The requested attribute from the appropriate module

    Raises:
        AttributeError: If the attribute is not found in any lazy import mapping
    """
    # === CIRCULAR DEPENDENCY RESOLUTION ===
    if name == 'main_bp':
        from .. import main_bp
        return main_bp

    # === TEST BACKWARD COMPATIBILITY ===
    if name in _LAZY_IMPORTS_INTERNAL:
        module_name, attr_name = _LAZY_IMPORTS_INTERNAL[name]
        # Use importlib for proper relative import handling
        module = importlib.import_module(module_name, package=__name__)
        return getattr(module, attr_name)

    # === DATABASE ACCESS (for test mocking) ===
    if name in _LAZY_IMPORTS_DATABASE:
        module_name, attr_name = _LAZY_IMPORTS_DATABASE[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Re-export the route functions
# pylint: disable=wrong-import-position  # Must come after __getattr__ definition for lazy imports
from .routes import export_data, export_size, import_data  # noqa: E402

__all__ = ['export_data', 'export_size', 'import_data']
