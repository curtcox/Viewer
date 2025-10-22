import json
from pathlib import Path
import unittest

from app import create_app
from database import db
from models import CID, Server


class TestGlomServerTemplate(unittest.TestCase):
    """Ensure the Glom server template extracts JSON values from CIDs."""

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
        self.user_id = "user-1"

        template_path = (
            Path(self.app.root_path)
            / "server_templates"
            / "definitions"
            / "glom.py"
        )
        definition = template_path.read_text(encoding="utf-8")
        self.server = Server(name="glom", definition=definition, user_id=self.user_id)
        db.session.add(self.server)
        db.session.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_user_id"] = self.user_id
            session["_fresh"] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _store_cid(self, cid_value: str, content: str) -> str:
        record = CID(
            path=f"/{cid_value}",
            file_data=content.encode("utf-8"),
            file_size=len(content),
            uploaded_by_user_id=self.user_id,
        )
        db.session.add(record)
        db.session.commit()
        return cid_value

    def test_extracts_value_using_query_parameter(self):
        cid_value = self._store_cid(
            "cid-json",
            json.dumps(
                {
                    "user": {
                        "profile": {"name": "Ada"},
                        "roles": ["admin", "editor"],
                    }
                }
            ),
        )

        response = self.client.get(
            f"/glom/{cid_value}?q=user.profile.name", follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("Content-Type", ""))

        html = response.get_data(as_text=True)
        self.assertIn("Glom result", html)
        self.assertIn("user.profile.name", html)
        self.assertIn("Ada", html)
        self.assertIn(cid_value, html)

    def test_missing_query_parameter_displays_notice(self):
        cid_value = self._store_cid("cid-empty", json.dumps({"value": 1}))

        response = self.client.get(f"/glom/{cid_value}", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Glom query missing", html)
        self.assertIn("Provide the `q` query parameter", html)

    def test_template_does_not_depend_on_server_name(self):
        cid_value = self._store_cid("cid-alt", json.dumps({"nested": {"target": 42}}))

        self.server.name = "json_explorer"
        db.session.commit()

        response = self.client.get(
            f"/json_explorer/{cid_value}?q=nested.target", follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Glom result", html)
        self.assertIn("nested.target", html)
        self.assertIn("42", html)


if __name__ == "__main__":
    unittest.main()
