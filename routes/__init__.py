"""Application route package."""
from flask import Blueprint

main_bp = Blueprint('main', __name__)

# pylint: disable=wrong-import-position
# Rationale: Blueprint must be created before importing route modules that register with it
# Import submodules to register routes with the blueprint.
from . import aliases  # noqa: F401,E402
from . import core  # noqa: F401,E402
from . import history  # noqa: F401,E402
from . import import_export  # noqa: F401,E402
from . import interactions  # noqa: F401,E402
from . import meta  # noqa: F401,E402
from . import openapi  # noqa: F401,E402
from . import route_details  # noqa: F401,E402
from . import routes_overview  # noqa: F401,E402
from . import search  # noqa: F401,E402
from . import secrets  # noqa: F401,E402
from . import servers  # noqa: F401,E402
from . import source  # noqa: F401,E402
from . import uploads  # noqa: F401,E402
from . import variables  # noqa: F401,E402

__all__ = ["main_bp"]
