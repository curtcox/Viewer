import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from flask import Flask

from cid_utils import serve_cid_content


class TestServeCidContent(unittest.TestCase):
    """Tests for content disposition and caching behavior when serving CID data."""

    _DEFAULT_CONTENT = object()

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.cid_content = SimpleNamespace(
            file_data=b"test content",
            created_at=datetime.now(timezone.utc),
        )

    def _serve(self, path, *, headers=None, content=_DEFAULT_CONTENT):
        with self.app.test_request_context(path, headers=headers or {}):
            payload = self.cid_content if content is self._DEFAULT_CONTENT else content
            return serve_cid_content(payload, path)

    def test_cid_only_no_content_disposition(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456"
        response = self._serve(path)
        self.assertIsNotNone(response)
        self.assertNotIn("Content-Disposition", response.headers)

    def test_cid_with_extension_no_content_disposition(self):
        for path in [
            "/bafybeihelloworld123456789012345678901234567890123456.txt",
            "/bafybeihelloworld123456789012345678901234567890123456.html",
            "/bafybeihelloworld123456789012345678901234567890123456.json",
            "/bafybeihelloworld123456789012345678901234567890123456.pdf",
        ]:
            with self.subTest(path=path):
                response = self._serve(path)
                self.assertIsNotNone(response)
                self.assertNotIn("Content-Disposition", response.headers)

    def test_cid_with_filename_sets_content_disposition(self):
        cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.document.txt", "document.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.report.pdf", "report.pdf"),
            ("/bafybeihelloworld123456789012345678901234567890123456.data.json", "data.json"),
            ("/bafybeihelloworld123456789012345678901234567890123456.page.html", "page.html"),
            ("/bafybeihelloworld123456789012345678901234567890123456.my-file.csv", "my-file.csv"),
            ("/bafybeihelloworld123456789012345678901234567890123456.test_file.py", "test_file.py"),
        ]

        for path, expected_filename in cases:
            with self.subTest(path=path):
                response = self._serve(path)
                self.assertIsNotNone(response)
                expected_header = f'attachment; filename="{expected_filename}"'
                self.assertEqual(response.headers.get("Content-Disposition"), expected_header)

    def test_cid_with_multiple_dots_in_filename(self):
        cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.my.data.file.txt", "my.data.file.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.version.1.2.3.json", "version.1.2.3.json"),
            ("/bafybeihelloworld123456789012345678901234567890123456.backup.2024.01.15.sql", "backup.2024.01.15.sql"),
        ]

        for path, expected_filename in cases:
            with self.subTest(path=path):
                response = self._serve(path)
                self.assertIsNotNone(response)
                expected_header = f'attachment; filename="{expected_filename}"'
                self.assertEqual(response.headers.get("Content-Disposition"), expected_header)

    def test_edge_cases(self):
        cases = [
            ("/abc.txt", None),
            ("/abc.document.txt", "document.txt"),
            ("/a.b.c", "b.c"),
        ]

        for path, expected_filename in cases:
            with self.subTest(path=path):
                response = self._serve(path)
                self.assertIsNotNone(response)
                if expected_filename:
                    expected_header = f'attachment; filename="{expected_filename}"'
                    self.assertEqual(response.headers.get("Content-Disposition"), expected_header)
                else:
                    self.assertNotIn("Content-Disposition", response.headers)

    def test_filename_with_special_characters(self):
        cases = [
            ("/bafybeihelloworld123456789012345678901234567890123456.file with spaces.txt", "file with spaces.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.file-with-dashes.txt", "file-with-dashes.txt"),
            ("/bafybeihelloworld123456789012345678901234567890123456.file_with_underscores.txt", "file_with_underscores.txt"),
        ]

        for path, expected_filename in cases:
            with self.subTest(path=path):
                response = self._serve(path)
                self.assertIsNotNone(response)
                expected_header = f'attachment; filename="{expected_filename}"'
                self.assertEqual(response.headers.get("Content-Disposition"), expected_header)

    def test_none_content_returns_none(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456.txt"
        self.assertIsNone(self._serve(path, content=None))

    def test_content_with_none_file_data_returns_none(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456.txt"
        empty_content = SimpleNamespace(file_data=None)
        self.assertIsNone(self._serve(path, content=empty_content))

    def test_caching_headers_still_work(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456.document.txt"
        response = self._serve(path)
        self.assertIsNotNone(response)
        self.assertIn("ETag", response.headers)
        self.assertIn("Cache-Control", response.headers)
        self.assertIn("Last-Modified", response.headers)
        self.assertIn("Content-Disposition", response.headers)

    def test_conditional_requests_with_filename(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456.document.txt"
        cid = path.lstrip("/").split(".")[0]
        etag_value = f'"{cid}"'
        response = self._serve(path, headers={'If-None-Match': etag_value})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 304)
        self.assertEqual(response.headers.get("ETag"), etag_value)

    def test_conditional_request_uses_if_modified_since_header(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456.note"
        response = self._serve(path, headers={'If-Modified-Since': 'Wed, 21 Oct 2015 07:28:00 GMT'})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 304)
        self.assertIn('Last-Modified', response.headers)
        self.assertIn('ETag', response.headers)

    def test_markdown_without_extension_renders_html_document(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456"
        markdown_content = SimpleNamespace(
            file_data=b"# Heading\n\n- item one\n- item two\n",
            created_at=self.cid_content.created_at,
        )

        response = self._serve(path, content=markdown_content)
        self.assertIsNotNone(response)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html')
        body = response.get_data(as_text=True)
        self.assertIn('<h1>Heading</h1>', body)
        self.assertIn('<li>item one</li>', body)

    def test_explicit_markdown_html_extension_renders_markdown(self):
        path = "/bafybeihelloworld123456789012345678901234567890123456.notes.md.html"
        markdown_content = SimpleNamespace(
            file_data=b"Plain text rendered as markdown",
            created_at=self.cid_content.created_at,
        )

        response = self._serve(path, content=markdown_content)
        self.assertIsNotNone(response)
        self.assertEqual(response.headers.get('Content-Type'), 'text/html')
        body = response.get_data(as_text=True)
        self.assertIn('<main class="markdown-body">', body)
        self.assertIn('Plain text rendered as markdown', body)


if __name__ == "__main__":
    unittest.main()
