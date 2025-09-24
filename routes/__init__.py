"""Application route package."""
from flask import Blueprint

main_bp = Blueprint('main', __name__)

# Import submodules to register routes with the blueprint.
from . import core  # noqa: F401,E402
from . import uploads  # noqa: F401,E402
from . import servers  # noqa: F401,E402
from . import variables  # noqa: F401,E402
from . import secrets  # noqa: F401,E402
from . import history  # noqa: F401,E402
from . import aliases  # noqa: F401,E402
from . import import_export  # noqa: F401,E402
from . import source  # noqa: F401,E402
from . import meta  # noqa: F401,E402

__all__ = ["main_bp"]
