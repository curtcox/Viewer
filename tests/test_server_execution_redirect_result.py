"""Tests covering server execution redirects for preview pages."""

import unittest
from datetime import datetime, timezone

from app import create_app
from database import db
from models import CID, Server


class TestServerExecutionRedirectResult(unittest.TestCase):
    """Ensure executing a server follows redirects to a CID-backed page."""

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.user_id = "preview-user"

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_user_id"] = self.user_id
            session["_fresh"] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_server(self, name: str, definition: str, *, enabled: bool = True) -> Server:
        server = Server(
            id=None,
            name=name,
            definition=definition,
            user_id=self.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            enabled=enabled,
        )
        db.session.add(server)
        db.session.commit()
        return server

    def test_follow_redirect_returns_cid_html(self):
        """Following the redirect should produce CID-backed HTML content."""

        server = self._create_server(
            "markdown",
            (
                "def main():\n"
                "    return \"\"\"<html><body><h1>Preview</h1></body></html>\"\"\"\n"
            ),
        )

        response = self.client.get(f"/{server.name}", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        final_path = response.request.path
        self.assertTrue(final_path.startswith("/"))
        self.assertNotEqual(final_path, f"/{server.name}")
        self.assertTrue(final_path.endswith(".html"))

        cid_value = final_path.lstrip("/").split(".", 1)[0]
        cid_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNotNone(cid_record)

        direct_response = self.client.get(final_path)
        self.assertEqual(response.data, direct_response.data)

    def test_server_enablement_controls_execution(self):
        server = self._create_server(
            "markdown",
            (
                "def main():\n"
                "    return \"\"\"<html><body><h1>Preview</h1></body></html>\"\"\"\n"
            ),
        )

        server.enabled = False
        db.session.commit()

        disabled_response = self.client.get(f"/{server.name}")
        self.assertEqual(disabled_response.status_code, 404)

        server.enabled = True
        db.session.commit()

        enabled_response = self.client.get(f"/{server.name}", follow_redirects=True)
        self.assertEqual(enabled_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
