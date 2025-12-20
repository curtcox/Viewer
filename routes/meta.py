"""Backward compatibility shim for routes.meta package.

This module maintains backward compatibility for code that imports from routes.meta
instead of the new routes.meta package. All functionality has been decomposed into
focused modules within routes/meta/.
"""

from __future__ import annotations

from routes.meta import inspect_path_metadata, meta_route

META_SOURCE_LINK = "/source/routes/meta.py"

__all__ = ["inspect_path_metadata", "meta_route", "META_SOURCE_LINK"]
