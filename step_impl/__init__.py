"""Gauge step implementations for SecureApp specs.

The Gauge Python runner imports this package directly. Without explicitly
importing the step modules the decorated functions never register, which causes
Gauge to report that every step definition is missing. Import the concrete step
modules at import time so the decorators execute and Gauge can discover the
implementations.
"""

# Import the source browser steps so Gauge registers the decorated functions.
# The module has side effects at import time and does not expose a public API,
# so we disable the unused import warning.
from . import source_steps  # noqa: F401
