"""Tests for the server definition validation endpoint."""

import textwrap
import unittest

from app import create_app
from database import db
from models import User


class TestServerDefinitionValidationRoute(unittest.TestCase):
    """Ensure the validation endpoint returns useful analysis."""

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

        self.user = User(
            id="user-1",
            email="user@example.com",
        )
        db.session.add(self.user)
        db.session.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_user_id"] = self.user.id
            session["_fresh"] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_validate_definition_returns_auto_main_parameters(self):
        """Valid auto main definitions should report parameter metadata."""

        definition = textwrap.dedent(
            """
            def helper():
                return "ignored"

            def main(name, count=1):
                return {"output": f"Hello {name}!" * int(count)}
            """
        ).strip()

        response = self.client.post(
            "/servers/validate-definition",
            json={"definition": definition},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["is_valid"])
        self.assertTrue(payload["auto_main"])
        self.assertEqual(payload["mode"], "main")

        parameters = payload.get("parameters", [])
        self.assertEqual(len(parameters), 2)
        self.assertEqual(parameters[0]["name"], "name")
        self.assertTrue(parameters[0]["required"])
        self.assertEqual(parameters[1]["name"], "count")
        self.assertFalse(parameters[1]["required"])

    def test_validate_definition_reports_syntax_error(self):
        """Syntax errors should be surfaced to the caller."""

        response = self.client.post(
            "/servers/validate-definition",
            json={"definition": "def main(:\n    pass"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["is_valid"])
        self.assertFalse(payload["auto_main"])
        self.assertEqual(payload["mode"], "query")
        self.assertGreater(len(payload.get("errors", [])), 0)

    def test_validate_definition_flags_unsupported_main_signature(self):
        """Unsupported auto main signatures should include helpful reasons."""

        definition = textwrap.dedent(
            """
            def main(*args):
                return {"output": "ok"}
            """
        ).strip()

        response = self.client.post(
            "/servers/validate-definition",
            json={"definition": definition},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["is_valid"])
        self.assertFalse(payload["auto_main"])
        self.assertTrue(payload["has_main"])
        self.assertGreater(len(payload.get("auto_main_errors", [])), 0)

    def test_validate_definition_available_without_authentication(self):
        """Definition validation remains accessible in the default workspace."""

        anonymous_client = self.app.test_client()
        response = anonymous_client.post(
            "/servers/validate-definition",
            json={"definition": "print('hi')"},
        )

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
