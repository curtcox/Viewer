"""Integration tests for server execution error pages."""
from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app
from database import db
from models import Server


class _SourceLinkParser(HTMLParser):
    """Collect ``/source`` hyperlink label pairs from rendered HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._collect = False
        self._current_href: str | None = None
        self._buffer: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href and href.startswith("/source/"):
                self._current_href = href
        elif tag == "code" and self._current_href:
            self._collect = True

    def handle_data(self, data: str) -> None:
        if self._collect:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self._collect:
            self._collect = False
        elif tag == "a" and self._current_href:
            label = "".join(self._buffer).strip()
            if label:
                self.links.append((self._current_href, label))
            self._current_href = None
            self._buffer = []


class TestServerExecutionErrorPages(unittest.TestCase):
    """Ensure server execution failures render enhanced error pages."""

    def setUp(self) -> None:
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

        template_path = (
            Path(self.app.root_path)
            / "reference_templates"
            / "servers"
            / "definitions"
            / "jinja_renderer.py"
        )
        definition = template_path.read_text(encoding="utf-8")
        self.server = Server(
            name="jinja_renderer",
            definition=definition,
        )
        db.session.add(self.server)
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_error_page_strips_project_root_and_links_sources(self) -> None:
        response = self.client.get("/jinja_renderer")

        self.assertEqual(response.status_code, 500)
        self.assertIn("text/html", response.headers["Content-Type"])

        html = response.get_data(as_text=True)
        normalized = html.replace("\\", "/")
        root_fragment = Path(self.app.root_path).resolve().as_posix()
        self.assertNotIn(
            root_fragment,
            normalized,
            msg="Error page should not include redundant absolute project prefixes",
        )

        parser = _SourceLinkParser()
        parser.feed(html)
        self.assertGreater(
            len(parser.links),
            0,
            msg="Stack trace should include at least one source hyperlink",
        )

        for href, label in parser.links:
            self.assertTrue(href.startswith("/source/"))
            expected_label = href[len("/source/") :]
            self.assertEqual(
                label,
                expected_label,
                msg="Source link label should match its /source relative path",
            )

        # After decomposition, check for the code_execution module instead of server_execution.py
        link_labels = {label for _, label in parser.links}
        self.assertTrue(
            "server_execution/code_execution.py" in link_labels or "server_execution.py" in link_labels,
            msg=f"Server execution frame should expose a /source link, found: {link_labels}",
        )

    def test_error_page_includes_server_details_and_arguments(self) -> None:
        self.server.definition = """
def main(request):
    raise ValueError("boom")
"""
        db.session.commit()

        response = self.client.get("/jinja_renderer?color=blue")

        self.assertEqual(response.status_code, 500)

        html = response.get_data(as_text=True)

        self.assertIn("Server source code", html)
        self.assertIn("codehilite", html)
        self.assertIn("ValueError", html)
        self.assertIn("Arguments passed to server", html)
        self.assertIn("/servers/jinja_renderer", html)
        self.assertIn("Stack trace with source links", html)

        # Arguments section should include the provided query parameter.
        self.assertIn("color", html)


if __name__ == "__main__":
    unittest.main()
