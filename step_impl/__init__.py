"""Gauge step implementations for Viewer specs.

The Gauge Python runner imports this package directly. Without explicitly
importing the step modules the decorated functions never register, which causes
Gauge to report that every step definition is missing. Import the concrete step
modules at import time so the decorators execute and Gauge can discover the
implementations.
"""

# Import each module that declares Gauge steps so the decorators execute during
# package import. The modules only provide side effects for registration, so we
# silence unused-import checks.
from . import alias_steps  # noqa: F401
from . import authorization_steps  # noqa: F401
from . import chaining_steps  # noqa: F401
from . import cid_editor_steps  # noqa: F401
from . import import_export_steps  # noqa: F401
from . import pipeline_debug_steps  # noqa: F401
from . import source_steps  # noqa: F401
from . import urleditor_steps  # noqa: F401
from . import web_steps  # noqa: F401
