#!/usr/bin/env python3
"""Integration tests for validate_import_export.py.

These tests verify the end-to-end functionality of the validation script,
including the main() function and real-world scenarios.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import from the parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from validate_import_export import (
    IMPORT_VALIDATION_RULES,
    ValidationReporter,
    discover_modules,
    main,
    validate_backward_compatibility,
    validate_circular_imports,
    validate_import_structure,
    validate_module_sizes,
    validate_syntax,
)


class TestMainFunction:
    """Tests for the main validation function."""

    def test_main_with_no_modules(self, capsys):
        """Test main() when no modules are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            original_viewer_path = os.environ.get('VIEWER_PATH')
            try:
                Path(tmpdir).joinpath('.git').mkdir()  # Make it look like a repo
                os.chdir(tmpdir)
                os.environ['VIEWER_PATH'] = tmpdir

                result = main()

                assert result == 1
                captured = capsys.readouterr()
                assert "No modules found" in captured.out
            finally:
                os.chdir(original_cwd)
                if original_viewer_path is not None:
                    os.environ['VIEWER_PATH'] = original_viewer_path
                elif 'VIEWER_PATH' in os.environ:
                    del os.environ['VIEWER_PATH']

    def test_main_with_valid_structure(self):
        """Test main() with a valid module structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create directory structure
            module_dir = base_path / 'routes' / 'import_export'
            module_dir.mkdir(parents=True)

            # Create valid modules
            (module_dir / 'module_a.py').write_text("""
# Module A
import os

def process_data():
    return "processed"
""")

            # Create compatibility shim
            shim_path = base_path / 'routes' / 'import_export.py'
            shim_path.write_text("""
# Compatibility shim
from routes.import_export.export_engine import export_data
from routes.import_export.import_engine import import_data
from routes.import_export.export_size import export_size
""")

            original_cwd = os.getcwd()
            original_viewer_path = os.environ.get('VIEWER_PATH')
            try:
                os.chdir(tmpdir)
                os.environ['VIEWER_PATH'] = tmpdir

                # Mock the validation rules to avoid real module checks
                with patch('validate_import_export.IMPORT_VALIDATION_RULES', {}):
                    result = main()

                # Should pass all validations
                assert result == 0
            finally:
                os.chdir(original_cwd)
                if original_viewer_path is not None:
                    os.environ['VIEWER_PATH'] = original_viewer_path
                elif 'VIEWER_PATH' in os.environ:
                    del os.environ['VIEWER_PATH']

    def test_main_with_syntax_error(self):
        """Test main() when there's a syntax error in a module."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create directory structure
            module_dir = base_path / 'routes' / 'import_export'
            module_dir.mkdir(parents=True)

            # Create module with syntax error
            (module_dir / 'broken.py').write_text("""
def broken_function(
    # Missing closing parenthesis
""")

            original_cwd = os.getcwd()
            original_viewer_path = os.environ.get('VIEWER_PATH')
            try:
                os.chdir(tmpdir)
                os.environ['VIEWER_PATH'] = tmpdir
                result = main()

                # Should fail due to syntax error
                assert result == 1
            finally:
                os.chdir(original_cwd)
                if original_viewer_path is not None:
                    os.environ['VIEWER_PATH'] = original_viewer_path
                elif 'VIEWER_PATH' in os.environ:
                    del os.environ['VIEWER_PATH']


class TestRealWorldScenarios:
    """Tests for real-world validation scenarios."""

    def test_validate_refactored_module_structure(self):
        """Test validating a properly refactored module structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            module_dir = base_path / 'routes' / 'import_export'
            module_dir.mkdir(parents=True)

            # Create a realistic module structure
            modules = {
                'export_engine.py': """
from cid_presenter import format_cid
from cid_utils import generate_cid

def export_data(data):
    return {"exported": True}
""",
                'import_engine.py': """
from cid_presenter import format_cid
from cid_utils import generate_cid

def import_data(data):
    return {"imported": True}
""",
                'export_size.py': """
def export_size(data):
    return len(str(data))
""",
                '__init__.py': """
# Package marker
""",
            }

            for name, content in modules.items():
                (module_dir / name).write_text(content)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Discover and validate
                discovered = discover_modules(base_path)
                assert len(discovered) == len(modules)

                # Validate syntax
                reporter = ValidationReporter()
                syntax_result = validate_syntax(discovered, reporter)
                assert syntax_result.passed is True

                # Validate sizes
                size_result = validate_module_sizes(discovered, reporter, threshold=1000)
                assert size_result.passed is True

            finally:
                os.chdir(original_cwd)

    def test_detect_accidental_circular_imports(self):
        """Test detecting circular imports in a refactored codebase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            module_dir = base_path / 'routes' / 'import_export'
            module_dir.mkdir(parents=True)

            # Create modules with circular dependencies
            (module_dir / 'module_a.py').write_text("""
from routes.import_export.module_b import helper_b

def function_a():
    return helper_b()
""")
            (module_dir / 'module_b.py').write_text("""
from routes.import_export.module_a import function_a

def helper_b():
    return function_a()
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                discovered = discover_modules(base_path)
                reporter = ValidationReporter()
                circular_result = validate_circular_imports(discovered, reporter)

                # Should detect the circular dependency
                assert circular_result.passed is False

            finally:
                os.chdir(original_cwd)

    def test_validate_large_module_detection(self):
        """Test that large modules are properly detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            module_dir = base_path / 'routes' / 'import_export'
            module_dir.mkdir(parents=True)

            # Create a large module (500 lines)
            large_content = '\n'.join([f'# Line {i}\ndef func_{i}(): pass' for i in range(500)])
            (module_dir / 'large_module.py').write_text(large_content)

            # Create a small module
            (module_dir / 'small_module.py').write_text('# Small module\n')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                discovered = discover_modules(base_path)
                reporter = ValidationReporter()

                # Should pass with high threshold (well above the actual size)
                result_high = validate_module_sizes(discovered, reporter, threshold=2000)
                assert result_high.passed is True

                # Should fail with low threshold (below the actual size)
                result_low = validate_module_sizes(discovered, reporter, threshold=100)
                assert result_low.passed is False

            finally:
                os.chdir(original_cwd)

    def test_backward_compatibility_validation_workflow(self):
        """Test the backward compatibility validation in a real scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            routes_dir = base_path / 'routes'
            routes_dir.mkdir()

            # Create a proper shim file
            shim_content = """
\"\"\"Backward compatibility shim for import_export.

This module maintains the public API while delegating to the refactored modules.
\"\"\"

from routes.import_export.export_engine import export_data
from routes.import_export.import_engine import import_data
from routes.import_export.export_size import export_size

__all__ = ['export_data', 'import_data', 'export_size']
"""
            (routes_dir / 'import_export.py').write_text(shim_content)

            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                reporter = ValidationReporter()
                result = validate_backward_compatibility(reporter)

                assert result.passed is True
                assert len(result.details) > 0
            finally:
                os.chdir(original_cwd)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_python_file(self):
        """Test validation with an empty Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / 'empty.py'
            module_path.write_text('')

            reporter = ValidationReporter()
            result = validate_syntax([str(module_path)], reporter)
            assert result.passed is True

    def test_module_with_only_comments(self):
        """Test validation with a file containing only comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / 'comments_only.py'
            module_path.write_text('# This is a comment\n# Another comment\n')

            reporter = ValidationReporter()
            result = validate_syntax([str(module_path)], reporter)
            assert result.passed is True

    def test_module_with_encoding_declaration(self):
        """Test validation with a file that has an encoding declaration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / 'encoded.py'
            module_path.write_text('# -*- coding: utf-8 -*-\nimport os\n')

            reporter = ValidationReporter()
            result = validate_syntax([str(module_path)], reporter)
            assert result.passed is True

    def test_nested_module_structure(self):
        """Test discovery with nested module structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            module_dir = base_path / 'routes' / 'import_export'

            # Create nested structure
            (module_dir / 'level1').mkdir(parents=True)
            (module_dir / 'level1' / 'level2').mkdir()

            (module_dir / 'root.py').write_text('# Root module')
            (module_dir / 'level1' / 'mid.py').write_text('# Mid-level module')
            (module_dir / 'level1' / 'level2' / 'deep.py').write_text('# Deep module')

            discovered = discover_modules(base_path)

            # Should find all three modules
            assert len(discovered) == 3
            assert any('root.py' in m for m in discovered)
            assert any('mid.py' in m for m in discovered)
            assert any('deep.py' in m for m in discovered)

    def test_import_structure_validation_with_complex_rules(self):
        """Test import structure validation with complex rule sets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / 'complex_module.py'
            module_path.write_text("""
from cid_presenter import format_cid
from cid_utils import generate_cid
from pathlib import Path
import os
import sys
""")

            complex_rules = {
                str(module_path): {
                    'required': [
                        ('from', 'cid_presenter', 'format_cid'),
                        ('from', 'cid_utils', 'generate_cid'),
                        ('from', 'pathlib', 'Path'),
                    ],
                    'forbidden': [
                        ('from', 'cid_utils', 'format_cid'),
                        ('import', 'deprecated_module'),
                    ]
                }
            }

            reporter = ValidationReporter()
            result = validate_import_structure(complex_rules, reporter)

            # Should pass all checks
            assert result.passed is True


class TestValidationReporting:
    """Tests for validation reporting and output."""

    def test_validation_details_are_comprehensive(self):
        """Test that validation results include comprehensive details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            modules = []
            for i in range(3):
                module_path = Path(tmpdir) / f'module_{i}.py'
                module_path.write_text(f'# Module {i}\n')
                modules.append(str(module_path))

            reporter = ValidationReporter()
            result = validate_syntax(modules, reporter)

            # Should have details for each module
            assert len(result.details) == 3
            assert all(f'module_{i}.py' in str(result.details) for i in range(3))

    def test_error_details_include_context(self):
        """Test that error details include useful context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / 'error_module.py'
            module_path.write_text('def broken(\n')  # Syntax error

            reporter = ValidationReporter()
            result = validate_syntax([str(module_path)], reporter)

            assert result.passed is False
            assert len(result.details) > 0
            # Details should mention the problematic module
            assert any('error_module.py' in detail for detail in result.details)


class TestPerformance:
    """Tests for performance and scalability."""

    def test_handles_many_small_modules(self):
        """Test validation with many small modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            module_dir = base_path / 'routes' / 'import_export'
            module_dir.mkdir(parents=True)

            # Create 50 small modules
            for i in range(50):
                (module_dir / f'module_{i:02d}.py').write_text(f'# Module {i}\n')

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                discovered = discover_modules(base_path)
                assert len(discovered) == 50

                reporter = ValidationReporter()
                result = validate_syntax(discovered, reporter)
                assert result.passed is True

            finally:
                os.chdir(original_cwd)

    def test_handles_very_large_module(self):
        """Test validation with a very large module."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / 'huge_module.py'

            # Create a module with 2000 lines
            lines = [f'# Line {i}' for i in range(2000)]
            module_path.write_text('\n'.join(lines))

            reporter = ValidationReporter()
            result = validate_syntax([str(module_path)], reporter)
            assert result.passed is True

            # Check size validation
            size_result = validate_module_sizes([str(module_path)], reporter, threshold=1000)
            assert size_result.passed is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
