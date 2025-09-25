import importlib
import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from flask import Flask

from unittest.mock import patch


class TestMarkdownShowcaseTemplateRendering(unittest.TestCase):
    """Regression tests for the markdown_showcase upload template rendering."""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.cid_utils = importlib.import_module("cid_utils")
        self.template_bytes = Path(
            "upload_templates/contents/markdown_showcase.md"
        ).read_bytes()

    def _serve_showcase(self, module=None, suffix: str = ""):
        module = module or self.cid_utils
        cid = module.generate_cid(self.template_bytes)
        cid_content = SimpleNamespace(
            file_data=self.template_bytes,
            created_at=datetime.now(timezone.utc),
        )
        path = f"/{cid}{suffix}"
        with self.app.test_request_context(path):
            return module.serve_cid_content(cid_content, path)

    def _load_cid_utils_without_markdown(self):
        spec = importlib.util.spec_from_file_location(
            "cid_utils_without_markdown",
            Path("cid_utils.py"),
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"markdown": None}):
            spec.loader.exec_module(module)
        return module

    def test_data_tables_render_for_text_upload_template(self):
        """Data tables should render as HTML when viewing the template upload."""
        response = self._serve_showcase()
        self.assertIsNotNone(response)

        self.assertEqual(response.headers.get("Content-Type"), "text/html")
        body = response.get_data(as_text=True)
        self.assertIn("<table", body, "The rendered page should include an HTML table")
        self.assertIn(
            "<td><code>- [ ] Pending item</code></td>",
            body,
            "Table cells from the showcase template should be preserved",
        )

    def test_images_and_embeds_render_for_text_upload_template(self):
        """Images and mermaid embeds should render when viewing the template upload."""
        response = self._serve_showcase()
        self.assertIsNotNone(response)

        self.assertEqual(response.headers.get("Content-Type"), "text/html")
        body = response.get_data(as_text=True)
        self.assertIn('<img', body, "The showcase HTML should contain an <img> tag")
        self.assertIn(
            'alt="Flow diagram placeholder"',
            body,
            "Image alt text from the showcase template should be preserved",
        )
        self.assertIn(
            '<code class="language-mermaid">',
            body,
            "Mermaid code fences should render with a language-specific class",
        )

    def test_data_tables_render_when_markdown_dependency_missing(self):
        """Even without python-markdown, the fallback renderer should build tables."""
        fallback_module = self._load_cid_utils_without_markdown()
        response = self._serve_showcase(module=fallback_module)
        self.assertIsNotNone(response)

        self.assertEqual(response.headers.get("Content-Type"), "text/html")
        body = response.get_data(as_text=True)
        self.assertIn(
            "<table",
            body,
            "Fallback renderer should build table markup for pipe tables",
        )
        self.assertIn(
            "<td><code>- [ ] Pending item</code></td>",
            body,
            "Fallback renderer should preserve inline formatting within tables",
        )

    def test_images_and_embeds_render_when_markdown_dependency_missing(self):
        """Fallback renderer should emit images and mermaid code blocks."""
        fallback_module = self._load_cid_utils_without_markdown()
        response = self._serve_showcase(module=fallback_module)
        self.assertIsNotNone(response)

        self.assertEqual(response.headers.get("Content-Type"), "text/html")
        body = response.get_data(as_text=True)
        self.assertIn('<img', body, "Fallback renderer should emit <img> tags")
        self.assertIn(
            'alt="Flow diagram placeholder"',
            body,
            "Fallback renderer should keep the image alt text",
        )
        self.assertIn(
            '<code class="language-mermaid">',
            body,
            "Fallback renderer should annotate mermaid code fences",
        )


if __name__ == "__main__":
    unittest.main()
