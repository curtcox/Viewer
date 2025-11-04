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

# Re-export everything from the package for backward compatibility
from db_access import *  # noqa: F403, F401
