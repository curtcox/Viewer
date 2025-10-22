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


def test_current_user_reverts_to_default_when_session_cleared() -> None:
    """Clearing the session mid-request should restore the default user."""

    with app.app_context():
        db.create_all()
        try:
            default_user = ensure_default_user()

            with app.test_request_context("/"):
                session["_user_id"] = "custom-user"
                assert current_user.id == "custom-user"

                session.pop("_user_id", None)
                assert current_user.id == default_user.id

            assert current_user.id == default_user.id
        finally:
            db.session.remove()
            db.drop_all()
