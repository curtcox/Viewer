"""Tests for error page path formatting and source link labels."""
from __future__ import annotations

import unittest
from html.parser import HTMLParser
import traceback
from unittest.mock import patch

from app import create_app
from database import db


class _SourceLinkParser(HTMLParser):
    """Collect source link href/text pairs from rendered HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._in_source_anchor = False
        self._collect_code_text = False
        self._current_href: str | None = None
        self._code_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'a':
            href = dict(attrs).get('href')
            if href and href.startswith('/source/'):
                self._in_source_anchor = True
                self._current_href = href
        elif tag == 'code' and self._in_source_anchor:
            self._collect_code_text = True

    def handle_endtag(self, tag: str) -> None:
        if tag == 'code' and self._collect_code_text:
            self._collect_code_text = False
        elif tag == 'a' and self._in_source_anchor:
            label = ''.join(self._code_parts).strip()
            if self._current_href is not None and label:
                self.links.append((self._current_href, label))
            self._in_source_anchor = False
            self._current_href = None
            self._code_parts = []

    def handle_data(self, data: str) -> None:
        if self._collect_code_text:
            self._code_parts.append(data)


def _raise_path_formatting_error():
    """Helper that raises an error to populate the traceback."""
    raise RuntimeError('Test error for path formatting')


def _trigger_error_chain():
    """Wrapper to ensure multiple frames point at this file."""
    _raise_path_formatting_error()


class TestErrorPagePathFormatting(unittest.TestCase):
    """Verify enhanced error page formatting for stack trace paths."""

    def setUp(self) -> None:
        self.app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
        with self.app.app_context():
            db.create_all()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_source_links_use_clean_relative_paths(self) -> None:
        """Rendered stack trace should avoid redundant prefixes and align labels with links."""
        with self.app.app_context():
            with self.app.test_request_context('/path-formatting-test'):
                try:
                    _trigger_error_chain()
                except RuntimeError as exc:
                    from routes.core import internal_error

                    html_content, status_code = internal_error(exc)

        self.assertEqual(status_code, 500)

        normalized_html = html_content.replace('\\', '/')
        root_fragment = self.app.root_path.replace('\\', '/')
        self.assertNotIn(
            root_fragment,
            normalized_html,
            msg='Stack trace should not include redundant project root prefixes',
        )

        parser = _SourceLinkParser()
        parser.feed(html_content)
        source_links = parser.links

        self.assertGreater(len(source_links), 0, 'Should collect source links from stack trace')
        for href, label in source_links:
            self.assertTrue(href.startswith('/source/'))
            expected_label = href[len('/source/'):]
            self.assertEqual(
                label,
                expected_label,
                msg='Link label should match the relative path used in the /source URL',
            )

    def test_removes_project_root_from_unmatched_paths(self) -> None:
        """Even when relative resolution fails, redundant project roots should be stripped."""
        project_root = self.app.root_path.replace('\\', '/')
        problematic_path = f"{project_root}/../external/server_execution.py"

        fake_frame = traceback.FrameSummary(
            problematic_path,
            123,
            'fake_function',
            line='raise RuntimeError("boom")',
        )

        with self.app.app_context():
            with self.app.test_request_context('/path-formatting-test'):
                with patch('traceback.extract_tb', return_value=[fake_frame]):
                    with patch('pathlib.Path.relative_to', side_effect=ValueError):
                        with patch('routes.source._get_tracked_paths', return_value=frozenset()):
                            with patch('pathlib.Path.rglob', return_value=iter(())):
                                try:
                                    raise RuntimeError('boom')
                                except RuntimeError as exc:
                                    from routes.core import internal_error

                                    html_content, status_code = internal_error(exc)

        self.assertEqual(status_code, 500)
        normalized_html = html_content.replace('\\', '/')
        self.assertNotIn(
            project_root,
            normalized_html,
            msg='Stack trace should not expose redundant absolute project prefixes',
        )


if __name__ == '__main__':
    unittest.main()
