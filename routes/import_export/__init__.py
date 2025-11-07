"""Import/export package for handling user data exports and imports."""
from __future__ import annotations

# Import the main blueprint from the parent routes module
# This avoids circular imports while allowing routes.py access to main_bp
def __getattr__(name: str):
    """Lazy import main_bp to avoid circular dependencies."""
    if name == 'main_bp':
        from .. import main_bp
        return main_bp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Re-export the route functions
from .routes import export_data, export_size, import_data

__all__ = ['export_data', 'export_size', 'import_data']
