"""Tests for uploading server test forms as reusable formdown pages."""

from datetime import datetime, timedelta, timezone
import unittest

from app import create_app
from database import db
from models import CID, Server, User


class TestServerTestPageUpload(unittest.TestCase):
    """Ensure the upload endpoint mirrors the server test form."""

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
            is_paid=True,
            current_terms_accepted=True,
            payment_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
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

    def _create_server(self, name: str, definition: str) -> Server:
        server = Server(
            id=None,
            name=name,
            definition=definition,
            user_id=self.user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(server)
        db.session.commit()
        return server

    def test_upload_generates_formdown_for_main_parameters(self):
        """Uploading should create a formdown page with defaults for main() parameters."""

        server = self._create_server(
            "greet",
            """
def main(name, times: int = 1):
    return {"output": name * int(times)}
""".strip(),
        )

        response = self.client.post(
            f"/servers/{server.name}/upload-test-page",
            json={"values": {"name": "Ada", "times": "3"}},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("redirect_url", payload)
        redirect_url = payload["redirect_url"]
        self.assertTrue(redirect_url.endswith(".md.html"))

        cid_value = redirect_url.split("/", 1)[1].split(".", 1)[0]
        cid_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNotNone(cid_record)

        content = cid_record.file_data.decode("utf-8")
        self.assertIn("@form", content)
        self.assertIn("action=\"/greet\"", content)
        self.assertIn("@name(name): [text", content)
        self.assertIn("value=\"Ada\"", content)
        self.assertIn("@times(times): [text", content)
        self.assertIn("value=\"3\"", content)

    def test_upload_generates_formdown_for_query_mode(self):
        """Servers without auto main should render query textarea defaults."""

        server = self._create_server(
            "lookup",
            """
def helper():
    return "ok"
""".strip(),
        )

        response = self.client.post(
            f"/servers/{server.name}/upload-test-page",
            json={"values": {"query": "foo=bar\npage=2"}},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        redirect_url = payload["redirect_url"]
        cid_value = redirect_url.split("/", 1)[1].split(".", 1)[0]
        cid_record = CID.query.filter_by(path=f"/{cid_value}").first()
        self.assertIsNotNone(cid_record)

        content = cid_record.file_data.decode("utf-8")
        self.assertIn("@query_parameters(Query parameters):", content)
        self.assertIn("value=\"foo=bar\\npage=2\"", content)

    def test_upload_requires_authentication(self):
        """Anonymous users should be redirected to authenticate."""

        server = self._create_server(
            "echo",
            """
def main(message: str):
    return message
""".strip(),
        )

        anonymous_client = self.app.test_client()
        response = anonymous_client.post(
            f"/servers/{server.name}/upload-test-page",
            json={"values": {"message": "hi"}},
        )

        self.assertEqual(response.status_code, 302)


if __name__ == "__main__":
    unittest.main()
