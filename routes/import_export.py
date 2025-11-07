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
)

__all__ = [
    'export_data',
    'export_size',
    'import_data',
    '_import_aliases',
    '_import_servers',
    '_import_variables',
    '_import_secrets',
]
