import unittest
from unittest.mock import patch

from traceback import FrameSummary
from typing import Dict, List

from app import create_app
from database import db
from routes.core import internal_error, _build_stack_trace
from text_function_runner import run_text_function


class TestInternalServerErrorPage(unittest.TestCase):
    """Tests for the customized 500 error page with stack trace links."""

    def setUp(self):
        self.app = create_app(
            {
                'TESTING': False,
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'WTF_CSRF_ENABLED': False,
            }
        )
        self.app.config['PROPAGATE_EXCEPTIONS'] = False

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_error_page_includes_source_links(self):
        with self.app.test_request_context('/broken'):
            try:
                raise RuntimeError('Intentional failure for testing')
            except RuntimeError as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)

        body = response
        self.assertIn('RuntimeError', body)
        self.assertIn('Intentional failure for testing', body)
        self.assertIn('href="/source/test_error_pages.py"', body)
        self.assertIn('<code>test_error_pages.py</code>', body)

    def test_stack_trace_links_when_repo_root_differs(self):
        with self.app.app_context():
            try:
                raise RuntimeError('boom')
            except RuntimeError as exc:
                mock_frame = FrameSummary(
                    '/Viewer/server_execution.py',
                    123,
                    'run_text_function',
                    line='code line',
                )
                with patch('routes.source._get_tracked_paths', return_value=frozenset({'server_execution.py'})):
                    with patch('routes.core.traceback.extract_tb', return_value=[mock_frame]):
                        frames = _build_stack_trace(exc)

        self.assertEqual(len(frames), 1)
        frame = frames[0]
        self.assertEqual(frame['display_path'], 'server_execution.py')
        self.assertEqual(frame['source_link'], '/source/server_execution.py')

    def test_stack_trace_for_syntax_error_uses_placeholder_filename(self):
        captured = None
        frames: List[Dict[str, object]] = []

        with self.app.app_context():
            try:
                run_text_function('what?', {})
            except Exception as exc:
                captured = exc
                frames = _build_stack_trace(exc)

        self.assertIsInstance(captured, SyntaxError)
        self.assertEqual(captured.filename, '<string>')

        display_paths = [frame['display_path'] for frame in frames]
        self.assertIn('test_error_pages.py', display_paths)
        self.assertIn('text_function_runner.py', display_paths)
        self.assertNotIn('<string>', display_paths)

        runner_frame = next(
            (f for f in frames if f['display_path'] == 'text_function_runner.py'),
            None,
        )
        self.assertIsNotNone(runner_frame, 'missing text_function_runner frame')
        self.assertEqual(runner_frame['source_link'], '/source/text_function_runner.py')

    def test_error_page_for_syntax_error_has_no_source_links(self):
        with self.app.test_request_context('/syntax-error'):
            try:
                run_text_function('what?', {})
            except Exception as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)
        self.assertIn('SyntaxError', response)
        self.assertIn('&lt;string&gt;', response)
        self.assertIn('href="/source/text_function_runner.py"', response)

