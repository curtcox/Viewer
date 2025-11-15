import unittest
from pathlib import Path

from app import create_app
from database import db
from models import CID, Server


class TestPygmentsServerTemplate(unittest.TestCase):
    """Ensure the Pygments server template highlights CID content."""

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
            / "reference_templates"
            / "servers"
            / "definitions"
            / "pygments.py"
        )
        definition = template_path.read_text(encoding="utf-8")
        self.server = Server(name="pygments", definition=definition)
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
        )
        db.session.add(record)
        db.session.commit()
        return cid_value

    def test_highlights_python_source_based_on_extension(self):
        cid_value = self._store_cid(
            "cid-python",
            """def greet(name):\n    return f'Hello {name}'\n""",
        )

        response = self.client.get(f"/pygments/{cid_value}.py", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("Content-Type", ""))

        html = response.get_data(as_text=True)
        self.assertIn("codehilite", html)
        self.assertIn("greet", html)
        self.assertIn("Rendering from CID", html)

    def test_template_does_not_depend_on_server_name(self):
        cid_value = self._store_cid("cid-alt", "print('ok')\n")

        self.server.name = "syntax_viewer"
        db.session.commit()

        response = self.client.get(f"/syntax_viewer/{cid_value}.py", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("codehilite", html)
        self.assertIn("print", html)


if __name__ == "__main__":
    unittest.main()
