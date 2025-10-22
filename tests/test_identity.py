from flask import session

from app import app
from database import db
from identity import current_user, ensure_default_user


def test_current_user_defaults_outside_request_context() -> None:
    """Ensure the fallback user does not leak request-specific identities."""

    with app.app_context():
        db.create_all()
        try:
            default_user = ensure_default_user()
            assert current_user.id == default_user.id

            with app.test_request_context("/"):
                session["_user_id"] = "custom-user"
                assert current_user.id == "custom-user"

            # Once the request context ends we should fall back to the default user.
            assert current_user.id == default_user.id
        finally:
            db.session.remove()
            db.drop_all()
