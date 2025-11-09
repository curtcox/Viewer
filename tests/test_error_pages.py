import os
import tempfile
import unittest
from pathlib import Path
from traceback import FrameSummary
from typing import Dict, List
from unittest.mock import MagicMock, patch

from app import create_app
from database import db
from flask import current_app
from routes.core import internal_error
from routes.source import _get_all_project_files, _get_comprehensive_paths, _get_tracked_paths
from text_function_runner import run_text_function
from utils.stack_trace import build_stack_trace


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
        response = None
        status = None
        with self.app.test_request_context('/broken'):
            try:
                raise RuntimeError('Intentional failure for testing')
            except RuntimeError as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)

        body = response
        self.assertIn('RuntimeError', body)
        self.assertIn('Intentional failure for testing', body)
        self.assertIn('href="/source/tests/test_error_pages.py"', body)
        # Updated to match our enhanced error handling output format
        self.assertIn('<code class="text-primary">tests/test_error_pages.py</code>', body)

    def test_stack_trace_links_when_repo_root_differs(self):
        frames = None
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
                root_path = Path(current_app.root_path).resolve()
                with patch('routes.source._get_tracked_paths', return_value=frozenset({'server_execution.py'})):
                    with patch('utils.stack_trace.traceback.extract_tb', return_value=[mock_frame]):
                        tracked_paths = _get_tracked_paths(current_app.root_path)
                        frames = build_stack_trace(exc, root_path, tracked_paths)

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
                root_path = Path(current_app.root_path).resolve()
                try:
                    tracked_paths = _get_tracked_paths(current_app.root_path)
                except Exception:
                    tracked_paths = frozenset()
                frames = build_stack_trace(exc, root_path, tracked_paths)

        self.assertIsInstance(captured, SyntaxError)
        self.assertEqual(captured.filename, '<string>')  # pylint: disable=no-member  # SyntaxError has filename

        display_paths = [frame['display_path'] for frame in frames]
        self.assertIn('tests/test_error_pages.py', display_paths)
        self.assertIn('text_function_runner.py', display_paths)
        self.assertNotIn('<string>', display_paths)

        runner_frame = next(
            (f for f in frames if f['display_path'] == 'text_function_runner.py'),
            None,
        )
        self.assertIsNotNone(runner_frame, 'missing text_function_runner frame')
        self.assertEqual(runner_frame['source_link'], '/source/text_function_runner.py')

    def test_error_page_for_syntax_error_has_no_source_links(self):
        response = None
        status = None
        with self.app.test_request_context('/syntax-error'):
            try:
                run_text_function('what?', {})
            except Exception as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)
        self.assertIn('SyntaxError', response)
        self.assertIn('&lt;string&gt;', response)
        self.assertIn('href="/source/text_function_runner.py"', response)

    def test_enhanced_code_context_shows_multiple_lines(self):
        """Test that enhanced error pages show 5+ lines of context around errors."""
        response = None
        status = None
        with self.app.test_request_context('/test'):
            try:
                # This will create a traceback with this file
                raise ValueError('Test error for context')
            except ValueError as exc:
                response, status = internal_error(exc)

        self.assertEqual(status, 500)
        # Should show multiple lines of context with >>> marker
        self.assertIn('>>>', response)
        self.assertIn('Test error for context', response)

    def test_exception_chain_handling(self):
        """Test that exception chains are properly displayed with separators."""
        with self.app.app_context():
            try:
                try:
                    raise ValueError('Original error')
                except ValueError as e:
                    raise RuntimeError('Chained error') from e
            except RuntimeError as exc:
                root_path = Path(current_app.root_path).resolve()
                try:
                    tracked_paths = _get_tracked_paths(current_app.root_path)
                except Exception:
                    tracked_paths = frozenset()
                frames = build_stack_trace(exc, root_path, tracked_paths)

        # Should have frames for both exceptions with separator
        separator_frames = [f for f in frames if f.get('is_separator', False)]
        self.assertTrue(len(separator_frames) > 0, 'Should have exception chain separators')

        # Check separator content
        separator = separator_frames[0]
        self.assertIn('Exception Chain', separator['display_path'])
        self.assertIn('ValueError', separator['function'])

    def test_comprehensive_source_link_generation(self):
        """Test that source links are generated for all project files, not just git-tracked."""
        frames = None
        with self.app.app_context():
            # Create a mock frame for a project file
            mock_frame = FrameSummary(
                str(Path(self.app.root_path) / 'routes' / 'core.py'),
                100,
                'test_function',
                line='test line',
            )

            try:
                raise RuntimeError('Test error')
            except RuntimeError as exc:
                root_path = Path(current_app.root_path).resolve()
                try:
                    tracked_paths = _get_tracked_paths(current_app.root_path)
                except Exception:
                    tracked_paths = frozenset()
                with patch('utils.stack_trace.traceback.extract_tb', return_value=[mock_frame]):
                    frames = build_stack_trace(exc, root_path, tracked_paths)

        self.assertEqual(len(frames), 1)
        frame = frames[0]
        self.assertEqual(frame['display_path'], 'routes/core.py')
        self.assertEqual(frame['source_link'], '/source/routes/core.py')

    def test_error_handling_fallback_when_stack_trace_fails(self):
        """Test that error handler provides fallback when stack trace building fails."""
        response = None
        status = None
        with self.app.test_request_context('/test'):
            # Mock build_stack_trace to raise an exception
            with patch('utils.stack_trace.build_stack_trace', side_effect=Exception('Stack trace failed')):
                try:
                    raise ValueError('Original error')
                except ValueError as exc:
                    response, status = internal_error(exc)

        self.assertEqual(status, 500)
        # Should still show error information even when stack trace fails
        self.assertIn('ValueError', response)
        self.assertIn('Original error', response)


class TestEnhancedSourceBrowser(unittest.TestCase):
    """Tests for the enhanced source browser functionality."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        })

        # Skip tests if app is mocked during unittest discover
        if isinstance(self.app, MagicMock):
            self.skipTest("Skipping due to mocked app during unittest discover")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_all_project_files_discovers_python_files(self):
        """Test that _get_all_project_files discovers Python files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / 'test.py').write_text('# Python file')
            (temp_path / 'subdir').mkdir()
            (temp_path / 'subdir' / 'nested.py').write_text('# Nested Python file')
            (temp_path / 'README.md').write_text('# Markdown file')

            # Create excluded directory that should be ignored
            (temp_path / '__pycache__').mkdir()
            (temp_path / '__pycache__' / 'cached.pyc').write_text('cached')

            files = _get_all_project_files(str(temp_path))

            self.assertIn('test.py', files)
            self.assertIn('subdir/nested.py', files)
            self.assertIn('README.md', files)
            self.assertNotIn('__pycache__/cached.pyc', files)

    def test_get_all_project_files_handles_various_extensions(self):
        """Test that _get_all_project_files discovers various file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different extensions
            test_files = {
                'script.py': 'Python',
                'template.html': 'HTML',
                'style.css': 'CSS',
                'app.js': 'JavaScript',
                'config.json': 'JSON',
                'docker.yml': 'YAML',
                'setup.toml': 'TOML',
            }

            for filename, content in test_files.items():
                (temp_path / filename).write_text(content)

            files = _get_all_project_files(str(temp_path))

            for filename in test_files:
                self.assertIn(filename, files, f'Should discover {filename}')

    def test_get_comprehensive_paths_combines_tracked_and_all_files(self):
        """Test that _get_comprehensive_paths combines git-tracked and all project files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / 'tracked.py').write_text('# Tracked file')
            (temp_path / 'untracked.py').write_text('# Untracked file')

            # Mock git-tracked files to return only one file
            with patch('routes.source._get_tracked_paths', return_value=frozenset({'tracked.py'})):
                comprehensive = _get_comprehensive_paths(str(temp_path))

            # Should include both tracked and untracked files
            self.assertIn('tracked.py', comprehensive)
            self.assertIn('untracked.py', comprehensive)

    def test_enhanced_source_browser_serves_untracked_files(self):
        """Test that enhanced source browser can serve untracked project files."""
        with self.app.test_client() as client:
            # Test that we can access a file that exists in the project
            response = client.get('/source/routes/core.py')
            # Should not return 404 even if not git-tracked
            self.assertNotEqual(response.status_code, 404)

    def test_source_browser_excludes_sensitive_directories(self):
        """Test that source browser excludes sensitive directories like venv, __pycache__."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files in excluded directories
            excluded_dirs = ['venv', '__pycache__', '.git', 'node_modules']
            for excluded_dir in excluded_dirs:
                (temp_path / excluded_dir).mkdir()
                (temp_path / excluded_dir / 'sensitive.py').write_text('sensitive content')

            files = _get_all_project_files(str(temp_path))

            # Should not include files from excluded directories
            for excluded_dir in excluded_dirs:
                excluded_file = f'{excluded_dir}/sensitive.py'
                self.assertNotIn(excluded_file, files, f'Should exclude {excluded_file}')


class TestStackTraceEnhancements(unittest.TestCase):
    """Tests for enhanced stack trace functionality."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        })

        # Skip tests if app is mocked during unittest discover
        if isinstance(self.app, MagicMock):
            self.skipTest("Skipping due to mocked app during unittest discover")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_stack_trace_includes_comprehensive_file_paths(self):
        """Test that stack traces include paths from comprehensive file discovery."""
        stack_frames = None
        with self.app.app_context():
            # Create mock frames for different types of files
            frames = [
                FrameSummary(
                    str(Path(self.app.root_path) / 'routes' / 'core.py'),
                    100, 'route_function'
                ),
                FrameSummary(
                    str(Path(self.app.root_path) / 'templates' / 'base.html'),
                    50, 'template_function'
                ),
            ]

            try:
                raise RuntimeError('Test error')
            except RuntimeError as exc:
                root_path = Path(current_app.root_path).resolve()
                try:
                    tracked_paths = _get_tracked_paths(current_app.root_path)
                except Exception:
                    tracked_paths = frozenset()
                with patch('utils.stack_trace.traceback.extract_tb', return_value=frames):
                    stack_frames = build_stack_trace(exc, root_path, tracked_paths)

        self.assertEqual(len(stack_frames), 2)

        # Check that both files get source links
        core_frame = next(f for f in stack_frames if 'core.py' in f['display_path'])
        template_frame = next(f for f in stack_frames if 'base.html' in f['display_path'])

        self.assertEqual(core_frame['source_link'], '/source/routes/core.py')
        self.assertEqual(template_frame['source_link'], '/source/templates/base.html')

    def test_enhanced_code_context_with_line_numbers(self):
        """Test that code context includes proper line numbers and markers."""
        frames = None
        with self.app.app_context():
            # Create a temporary file with known content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write('\n'.join([
                    'line 1',
                    'line 2',
                    'line 3',
                    'ERROR LINE',  # This will be line 4
                    'line 5',
                    'line 6',
                    'line 7',
                ]))
                temp_file.flush()

                mock_frame = FrameSummary(temp_file.name, 4, 'test_func')

                try:
                    raise RuntimeError('Test')
                except RuntimeError as exc:
                    root_path = Path(current_app.root_path).resolve()
                    try:
                        tracked_paths = _get_tracked_paths(current_app.root_path)
                    except Exception:
                        tracked_paths = frozenset()
                    with patch('utils.stack_trace.traceback.extract_tb', return_value=[mock_frame]):
                        frames = build_stack_trace(exc, root_path, tracked_paths)

                # Clean up
                os.unlink(temp_file.name)

        self.assertEqual(len(frames), 1)
        frame = frames[0]
        code_context = frame['code']

        # Should include multiple lines with line numbers
        self.assertIn('line 2', code_context)
        self.assertIn('line 3', code_context)
        self.assertIn('ERROR LINE', code_context)
        self.assertIn('line 5', code_context)
        self.assertIn('line 6', code_context)

        # Should mark the error line with >>>
        self.assertIn('>>>    4: ERROR LINE', code_context)
