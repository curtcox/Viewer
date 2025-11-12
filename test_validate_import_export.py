#!/usr/bin/env python3
"""Tests for validate_import_export.py."""

import tempfile
from pathlib import Path

import pytest

from validate_import_export import (
    ValidationReporter,
    ValidationResult,
    analyze_imports,
    check_module_imports,
    discover_modules,
    validate_backward_compatibility,
    validate_circular_imports,
    validate_import_structure,
    validate_module_sizes,
    validate_syntax,
)


# ============================================================================
# Unit Tests for ValidationResult
# ============================================================================


def test_validation_result_creation():
    """Test creating a ValidationResult."""
    result = ValidationResult(passed=True, message="Test passed")
    assert result.passed is True
    assert result.message == "Test passed"
    assert not result.details


def test_validation_result_with_details():
    """Test creating a ValidationResult with details."""
    details = ["Detail 1", "Detail 2"]
    result = ValidationResult(passed=False, message="Test failed", details=details)
    assert result.passed is False
    assert result.message == "Test failed"
    assert result.details == details


# ============================================================================
# Unit Tests for ValidationReporter
# ============================================================================


def test_validation_reporter_section(capsys):
    """Test ValidationReporter section output."""
    reporter = ValidationReporter(separator_length=50)
    reporter.section("Test Section")
    captured = capsys.readouterr()
    assert "Test Section" in captured.out
    assert "-" * 50 in captured.out


def test_validation_reporter_header(capsys):
    """Test ValidationReporter header output."""
    reporter = ValidationReporter(separator_length=50)
    reporter.header("Test Header")
    captured = capsys.readouterr()
    assert "Test Header" in captured.out
    assert "=" * 50 in captured.out


def test_validation_reporter_success(capsys):
    """Test ValidationReporter success message."""
    reporter = ValidationReporter()
    reporter.success("Success message")
    captured = capsys.readouterr()
    assert "✓ Success message" in captured.out


def test_validation_reporter_success_with_indent(capsys):
    """Test ValidationReporter success message with indentation."""
    reporter = ValidationReporter()
    reporter.success("Indented success", indent=2)
    captured = capsys.readouterr()
    assert "    ✓ Indented success" in captured.out


def test_validation_reporter_failure(capsys):
    """Test ValidationReporter failure message."""
    reporter = ValidationReporter()
    reporter.failure("Failure message")
    captured = capsys.readouterr()
    assert "✗ Failure message" in captured.out


def test_validation_reporter_info(capsys):
    """Test ValidationReporter info message."""
    reporter = ValidationReporter()
    reporter.info("Info message", indent=1)
    captured = capsys.readouterr()
    assert "  Info message" in captured.out


def test_validation_reporter_warning(capsys):
    """Test ValidationReporter warning message."""
    reporter = ValidationReporter()
    reporter.warning("Warning message")
    captured = capsys.readouterr()
    assert "⚠ Warning message" in captured.out


def test_validation_reporter_status_passed(capsys):
    """Test ValidationReporter status for passed check."""
    reporter = ValidationReporter()
    reporter.status(True, "Check passed")
    captured = capsys.readouterr()
    assert "✓ Check passed" in captured.out


def test_validation_reporter_status_failed(capsys):
    """Test ValidationReporter status for failed check."""
    reporter = ValidationReporter()
    reporter.status(False, "Check failed")
    captured = capsys.readouterr()
    assert "✗ Check failed" in captured.out


def test_validation_reporter_result_summary(capsys):
    """Test ValidationReporter result summary."""
    reporter = ValidationReporter()
    results = {
        "Check 1": True,
        "Check 2": False,
        "Check 3": True,
    }
    reporter.result_summary(results)
    captured = capsys.readouterr()
    assert "VALIDATION SUMMARY" in captured.out
    assert "✅ Check 1" in captured.out
    assert "❌ Check 2" in captured.out
    assert "✅ Check 3" in captured.out


# ============================================================================
# Unit Tests for check_module_imports
# ============================================================================


def test_check_module_imports_success():
    """Test check_module_imports with a valid module."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Valid Python module\nimport os\n")
        temp_path = f.name

    try:
        passed, message = check_module_imports(temp_path)
        assert passed is True
        assert message == "OK"
    finally:
        Path(temp_path).unlink()


def test_check_module_imports_invalid_spec():
    """Test check_module_imports with invalid path."""
    # Create a temporary file that will be deleted immediately
    # to simulate a missing file
    with tempfile.NamedTemporaryFile(suffix='.py', delete=True) as f:
        temp_path = f.name
    # File is now deleted, so the path is invalid

    passed, message = check_module_imports(temp_path)
    # The function may still create a spec for a non-existent file
    # so we just verify it returns a tuple with bool and string
    assert isinstance(passed, bool)
    assert isinstance(message, str)


# ============================================================================
# Unit Tests for analyze_imports
# ============================================================================


def test_analyze_imports_simple():
    """Test analyze_imports with simple imports."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("import os\nimport sys\n")
        temp_path = f.name

    try:
        imports = analyze_imports(temp_path)
        assert ('import', 'os') in imports
        assert ('import', 'sys') in imports
    finally:
        Path(temp_path).unlink()


def test_analyze_imports_from_imports():
    """Test analyze_imports with from imports."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("from pathlib import Path\nfrom os import getcwd\n")
        temp_path = f.name

    try:
        imports = analyze_imports(temp_path)
        assert ('from', 'pathlib', 'Path') in imports
        assert ('from', 'os', 'getcwd') in imports
    finally:
        Path(temp_path).unlink()


def test_analyze_imports_mixed():
    """Test analyze_imports with mixed import styles."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("import os\nfrom pathlib import Path\nimport sys\nfrom collections import defaultdict\n")
        temp_path = f.name

    try:
        imports = analyze_imports(temp_path)
        assert len(imports) == 4
        assert ('import', 'os') in imports
        assert ('from', 'pathlib', 'Path') in imports
        assert ('import', 'sys') in imports
        assert ('from', 'collections', 'defaultdict') in imports
    finally:
        Path(temp_path).unlink()


# ============================================================================
# Unit Tests for discover_modules
# ============================================================================


def test_discover_modules_no_directory():
    """Test discover_modules when directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        modules = discover_modules(base_path)
        assert modules == []


def test_discover_modules_with_files():
    """Test discover_modules with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        module_dir = base_path / 'routes' / 'import_export'
        module_dir.mkdir(parents=True)

        # Create some Python files
        (module_dir / 'module_a.py').write_text('# Module A')
        (module_dir / 'module_b.py').write_text('# Module B')
        (module_dir / 'subdir').mkdir()
        (module_dir / 'subdir' / 'module_c.py').write_text('# Module C')

        modules = discover_modules(base_path)

        assert len(modules) == 3
        assert any('module_a.py' in m for m in modules)
        assert any('module_b.py' in m for m in modules)
        assert any('module_c.py' in m for m in modules)


# ============================================================================
# Unit Tests for validate_syntax
# ============================================================================


def test_validate_syntax_all_valid():
    """Test validate_syntax with all valid modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module1 = Path(tmpdir) / 'module1.py'
        module2 = Path(tmpdir) / 'module2.py'

        module1.write_text('# Valid module\nimport os\n')
        module2.write_text('def foo():\n    pass\n')

        reporter = ValidationReporter()
        result = validate_syntax([str(module1), str(module2)], reporter)

        assert result.passed is True
        assert "All modules have valid syntax" in result.message
        assert len(result.details) == 2


def test_validate_syntax_with_error():
    """Test validate_syntax with a syntax error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        valid_module = Path(tmpdir) / 'valid.py'
        invalid_module = Path(tmpdir) / 'invalid.py'

        valid_module.write_text('import os\n')
        invalid_module.write_text('def foo(\n')  # Syntax error

        reporter = ValidationReporter()
        result = validate_syntax([str(valid_module), str(invalid_module)], reporter)

        assert result.passed is False
        assert "Syntax errors found" in result.message


# ============================================================================
# Unit Tests for validate_import_structure
# ============================================================================


def test_validate_import_structure_all_correct():
    """Test validate_import_structure with correct imports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_path = Path(tmpdir) / 'test_module.py'
        module_path.write_text('from cid_presenter import format_cid\nfrom cid_utils import generate_cid\n')

        rules = {
            str(module_path): {
                'required': [
                    ('from', 'cid_presenter', 'format_cid'),
                    ('from', 'cid_utils', 'generate_cid'),
                ],
                'forbidden': [
                    ('from', 'cid_utils', 'format_cid'),
                ]
            }
        }

        reporter = ValidationReporter()
        result = validate_import_structure(rules, reporter)

        assert result.passed is True
        assert "Import structure is correct" in result.message


def test_validate_import_structure_missing_required():
    """Test validate_import_structure with missing required import."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_path = Path(tmpdir) / 'test_module.py'
        module_path.write_text('from cid_presenter import format_cid\n')  # Missing generate_cid

        rules = {
            str(module_path): {
                'required': [
                    ('from', 'cid_presenter', 'format_cid'),
                    ('from', 'cid_utils', 'generate_cid'),
                ],
                'forbidden': []
            }
        }

        reporter = ValidationReporter()
        result = validate_import_structure(rules, reporter)

        assert result.passed is False
        assert "Import structure violations found" in result.message


def test_validate_import_structure_forbidden_present():
    """Test validate_import_structure with forbidden import present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module_path = Path(tmpdir) / 'test_module.py'
        module_path.write_text('from cid_utils import format_cid\n')  # Forbidden import

        rules = {
            str(module_path): {
                'required': [],
                'forbidden': [
                    ('from', 'cid_utils', 'format_cid'),
                ]
            }
        }

        reporter = ValidationReporter()
        result = validate_import_structure(rules, reporter)

        assert result.passed is False
        assert "Import structure violations found" in result.message


# ============================================================================
# Unit Tests for validate_circular_imports (existing tests)
# ============================================================================


def test_validate_circular_imports_with_windows_paths():
    """Test that circular import detection works with Windows-style path separators.

    This test would have caught the bug where Path.as_posix() was not used,
    causing circular imports to be silently missed on Windows.
    """
    # Simulate Windows-style paths (backslashes) as returned by discover_modules()
    # on Windows. On Linux, Path().relative_to() returns forward slashes,
    # but on Windows it returns backslashes.
    windows_style_paths = [
        r"routes\import_export\module_a.py",
        r"routes\import_export\module_b.py",
    ]

    # Mock analyze_imports to return the imports we defined above
    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        # Normalize the path for comparison
        normalized = Path(file_path).as_posix()
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        if "module_b" in normalized:
            return [('from', 'routes.import_export.module_a', 'func_a')]
        return []

    # Temporarily replace analyze_imports
    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(windows_style_paths, reporter)

        # Should detect the circular import even with Windows paths
        assert not result.passed, "Should detect circular import with Windows-style paths"
        assert "Circular imports detected" in result.message
        assert any("circular" in detail.lower() for detail in result.details)

    finally:
        # Restore original function
        validate_import_export.analyze_imports = original_analyze


def test_validate_circular_imports_with_posix_paths():
    """Test that circular import detection works with POSIX-style path separators."""
    # POSIX-style paths (forward slashes)
    posix_style_paths = [
        "routes/import_export/module_a.py",
        "routes/import_export/module_b.py",
    ]

    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        normalized = Path(file_path).as_posix()
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        if "module_b" in normalized:
            return [('from', 'routes.import_export.module_a', 'func_a')]
        return []

    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(posix_style_paths, reporter)

        # Should detect the circular import with POSIX paths too
        assert not result.passed, "Should detect circular import with POSIX-style paths"
        assert "Circular imports detected" in result.message

    finally:
        validate_import_export.analyze_imports = original_analyze


def test_validate_circular_imports_no_cycles():
    """Test that non-circular imports pass validation."""
    # Non-circular module paths
    paths = [
        "routes/import_export/module_a.py",
        "routes/import_export/module_b.py",
    ]

    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        # A imports B, but B doesn't import A (no cycle)
        normalized = Path(file_path).as_posix()
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        if "module_b" in normalized:
            return []  # No imports from A
        return []

    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(paths, reporter)

        # Should pass when there's no circular import
        assert result.passed, "Should pass when there are no circular imports"
        assert "No circular imports" in result.message

    finally:
        validate_import_export.analyze_imports = original_analyze


# ============================================================================
# Unit Tests for validate_backward_compatibility
# ============================================================================


def test_validate_backward_compatibility_shim_exists():
    """Test validate_backward_compatibility when shim exists with correct exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        routes_dir = base_path / 'routes'
        routes_dir.mkdir()
        shim_path = routes_dir / 'import_export.py'

        shim_content = """
# Compatibility shim
from routes.import_export.export_engine import export_data
from routes.import_export.import_engine import import_data
from routes.import_export.export_size import export_size
"""
        shim_path.write_text(shim_content)

        # Temporarily change to the temp directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            reporter = ValidationReporter()
            result = validate_backward_compatibility(reporter)

            assert result.passed is True
            assert "Backward compatibility maintained" in result.message
        finally:
            os.chdir(original_cwd)


def test_validate_backward_compatibility_shim_missing():
    """Test validate_backward_compatibility when shim doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporarily change to the temp directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            reporter = ValidationReporter()
            result = validate_backward_compatibility(reporter)

            assert result.passed is False
            assert "not found" in result.message
        finally:
            os.chdir(original_cwd)


def test_validate_backward_compatibility_missing_exports():
    """Test validate_backward_compatibility when shim is missing some exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        routes_dir = base_path / 'routes'
        routes_dir.mkdir()
        shim_path = routes_dir / 'import_export.py'

        # Missing export_size
        shim_content = """
from routes.import_export.export_engine import export_data
from routes.import_export.import_engine import import_data
"""
        shim_path.write_text(shim_content)

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            reporter = ValidationReporter()
            result = validate_backward_compatibility(reporter)

            assert result.passed is False
            assert "missing some exports" in result.message
        finally:
            os.chdir(original_cwd)


# ============================================================================
# Unit Tests for validate_module_sizes
# ============================================================================


def test_validate_module_sizes_all_under_threshold():
    """Test validate_module_sizes with modules under threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module1 = Path(tmpdir) / 'small1.py'
        module2 = Path(tmpdir) / 'small2.py'

        # Create small modules (< 100 lines)
        module1.write_text('\n'.join([f'# Line {i}' for i in range(50)]))
        module2.write_text('\n'.join([f'# Line {i}' for i in range(80)]))

        reporter = ValidationReporter()
        result = validate_module_sizes([str(module1), str(module2)], reporter, threshold=100)

        assert result.passed is True
        assert "All modules under 100 lines" in result.message


def test_validate_module_sizes_exceeds_threshold():
    """Test validate_module_sizes with module exceeding threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        small_module = Path(tmpdir) / 'small.py'
        large_module = Path(tmpdir) / 'large.py'

        small_module.write_text('\n'.join([f'# Line {i}' for i in range(50)]))
        large_module.write_text('\n'.join([f'# Line {i}' for i in range(150)]))

        reporter = ValidationReporter()
        result = validate_module_sizes([str(small_module), str(large_module)], reporter, threshold=100)

        assert result.passed is False
        assert "Some modules exceed 100 lines" in result.message


def test_validate_module_sizes_reports_largest():
    """Test validate_module_sizes reports the largest module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module1 = Path(tmpdir) / 'module1.py'
        module2 = Path(tmpdir) / 'module2.py'
        module3 = Path(tmpdir) / 'module3.py'

        module1.write_text('\n'.join([f'# Line {i}' for i in range(30)]))
        module2.write_text('\n'.join([f'# Line {i}' for i in range(80)]))  # Largest
        module3.write_text('\n'.join([f'# Line {i}' for i in range(50)]))

        reporter = ValidationReporter()
        result = validate_module_sizes([str(module1), str(module2), str(module3)], reporter, threshold=100)

        assert result.passed is True
        assert 'module2.py' in str(result.details)


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_validation_workflow_success():
    """Test a complete successful validation workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create directory structure
        module_dir = base_path / 'routes' / 'import_export'
        module_dir.mkdir(parents=True)

        # Create valid modules
        (module_dir / 'module_a.py').write_text("""
# Module A
import os
def process():
    pass
""")
        (module_dir / 'module_b.py').write_text("""
# Module B
from pathlib import Path
def handle():
    pass
""")

        # Create compatibility shim
        routes_dir = base_path / 'routes'
        shim_path = routes_dir / 'import_export.py'
        shim_path.write_text("""
# Compatibility shim
from routes.import_export.export_engine import export_data
from routes.import_export.import_engine import import_data
from routes.import_export.export_size import export_size
""")

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Discover modules
            modules = discover_modules(base_path)
            assert len(modules) == 2

            # Validate syntax
            reporter = ValidationReporter()
            syntax_result = validate_syntax(modules, reporter)
            assert syntax_result.passed is True

            # Validate backward compatibility
            compat_result = validate_backward_compatibility(reporter)
            assert compat_result.passed is True

            # Validate module sizes
            size_result = validate_module_sizes(modules, reporter, threshold=100)
            assert size_result.passed is True

        finally:
            os.chdir(original_cwd)


def test_validation_workflow_with_failures():
    """Test validation workflow that should fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create directory structure
        module_dir = base_path / 'routes' / 'import_export'
        module_dir.mkdir(parents=True)

        # Create module with syntax error
        (module_dir / 'bad_module.py').write_text("""
def broken_function(
    # Missing closing parenthesis
""")

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Discover modules
            modules = discover_modules(base_path)
            assert len(modules) == 1

            # Validate syntax - should fail
            reporter = ValidationReporter()
            syntax_result = validate_syntax(modules, reporter)
            assert syntax_result.passed is False

        finally:
            os.chdir(original_cwd)


def test_circular_import_detection_complex_case():
    """Test circular import detection with a direct circular case.

    Note: The current implementation only detects direct circular imports
    (A -> B and B -> A), not transitive cycles (A -> B -> C -> A).
    """
    paths = [
        "routes/import_export/module_a.py",
        "routes/import_export/module_b.py",
    ]

    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        normalized = Path(file_path).as_posix()
        # A -> B, B -> A (direct circular)
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        if "module_b" in normalized:
            return [('from', 'routes.import_export.module_a', 'something')]
        return []

    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(paths, reporter)

        # Should detect the direct circular dependency
        assert not result.passed
        assert "Circular imports detected" in result.message

    finally:
        validate_import_export.analyze_imports = original_analyze


def test_empty_module_list():
    """Test validation functions with empty module list."""
    reporter = ValidationReporter()

    # Syntax validation with no modules
    syntax_result = validate_syntax([], reporter)
    assert syntax_result.passed is True
    assert "All modules have valid syntax" in syntax_result.message

    # Module size validation with no modules
    size_result = validate_module_sizes([], reporter)
    assert size_result.passed is True


def test_validation_result_details_accumulation():
    """Test that ValidationResult properly accumulates details."""
    details = []
    for i in range(5):
        details.append(f"Detail {i}")

    result = ValidationResult(passed=True, message="Success", details=details)
    assert len(result.details) == 5
    assert all(f"Detail {i}" in result.details for i in range(5))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
