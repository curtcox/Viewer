"""Legacy compatibility shim for db_access.

This module maintains backward compatibility by re-exporting all functions
from the new db_access package structure. The code has been split into
domain-specific modules:

- db_access/servers.py: Server CRUD operations
- db_access/aliases.py: Alias CRUD operations
- db_access/variables.py: Variable CRUD operations
- db_access/secrets.py: Secret CRUD operations
- db_access/cids.py: CID management
- db_access/page_views.py: Page view tracking
- db_access/interactions.py: Entity interactions
- db_access/invocations.py: Server invocations
- db_access/profile.py: User profile data
- db_access/_common.py: Shared utilities

All imports from this module continue to work, but new code should
import directly from db_access or the specific submodules.
"""
# pylint: disable=undefined-all-variable  # __all__ dynamically constructed from _exports module

from __future__ import annotations

from typing import TYPE_CHECKING

from db_access import _exports
from db_access._exports import LEGACY_DEFAULTS

__all__ = list(_exports.__all__)  # Names dynamically injected via globals().update()
globals().update(_exports.EXPORTS)
globals().update(LEGACY_DEFAULTS)

if TYPE_CHECKING:  # pragma: no cover
    pass
