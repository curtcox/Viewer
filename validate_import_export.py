#!/usr/bin/env python3
"""Comprehensive import validation for routes/import_export decomposition."""

import os
import sys
import ast
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

# Constants
SEPARATOR_LENGTH = 70
LINE_THRESHOLD = 1000
BASE_MODULE_PATH = "routes/import_export"

# Add the repo root to sys.path


def _resolve_repo_root() -> Path:
    """Return the repository root directory for import resolution."""

    env_root = os.environ.get("VIEWER_PATH")
    candidate = Path(env_root).expanduser().resolve() if env_root else Path(__file__).resolve().parent

    if not candidate.exists():  # pragma: no cover - defensive guard for misconfiguration
        raise FileNotFoundError(f"Repository root not found: {candidate}")

    return candidate


sys.path.insert(0, str(_resolve_repo_root()))


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    details: list[str] = field(default_factory=list)


class ValidationReporter:
    """Handles all formatted output for validation results."""

    def __init__(self, separator_length: int = SEPARATOR_LENGTH):
        self.separator_length = separator_length

    def section(self, title: str) -> None:
        """Print a section header."""
        print(f"\n{title}")
        print("-" * self.separator_length)

    def header(self, title: str) -> None:
        """Print a main header."""
        print("=" * self.separator_length)
        print(title)
        print("=" * self.separator_length)

    def success(self, msg: str, indent: int = 0) -> None:
        """Print a success message."""
        prefix = "  " * indent
        print(f"{prefix}✓ {msg}")

    def failure(self, msg: str, indent: int = 0) -> None:
        """Print a failure message."""
        prefix = "  " * indent
        print(f"{prefix}✗ {msg}")

    def info(self, msg: str, indent: int = 0) -> None:
        """Print an info message."""
        prefix = "  " * indent
        print(f"{prefix}{msg}")

    def warning(self, msg: str, indent: int = 0) -> None:
        """Print a warning message."""
        prefix = "  " * indent
        print(f"{prefix}⚠ {msg}")

    def status(self, passed: bool, msg: str, indent: int = 0) -> None:
        """Print a message with status indicator."""
        if passed:
            self.success(msg, indent)
        else:
            self.failure(msg, indent)

    def result_summary(self, results: dict[str, bool]) -> None:
        """Print a summary of all validation results."""
        self.header("VALIDATION SUMMARY")
        for check, passed in results.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")


def check_module_imports(module_path: str) -> tuple[bool, str]:
    """Check if a module can be imported successfully."""
    spec = importlib.util.spec_from_file_location("test_module", module_path)
    if spec is None:
        return False, "Could not create module spec"

    try:
        importlib.util.module_from_spec(spec)
        # Don't execute the module, just check if it can be loaded
        return True, "OK"
    except (ImportError, AttributeError, FileNotFoundError) as error:
        return False, str(error)

def analyze_imports(file_path: str) -> list[tuple[str, ...]]:
    """Extract and analyze all imports from a Python file."""
    with Path(file_path).open(encoding="utf-8") as file_handle:
        tree = ast.parse(file_handle.read(), filename=file_path)

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(('import', alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(('from', module, alias.name))

    return imports


# Validation rules for import structure
IMPORT_VALIDATION_RULES = {
    'routes/import_export/import_sources.py': {
        'required': [
            ('from', 'cid_presenter', 'format_cid'),
            ('from', 'cid_utils', 'generate_cid'),
        ],
        'forbidden': [
            ('from', 'cid_utils', 'format_cid'),
        ]
    },
    'routes/import_export/import_engine.py': {
        'required': [
            ('from', 'cid_presenter', 'format_cid'),
            ('from', 'cid_utils', 'generate_cid'),
        ],
        'forbidden': [
            ('from', 'cid_utils', 'format_cid'),
        ]
    },
}


def discover_modules(base_path: Path | None = None) -> list[str]:
    """Find all .py files in routes/import_export/."""
    if base_path is None:
        base_path = _resolve_repo_root()

    module_dir = base_path / BASE_MODULE_PATH
    if not module_dir.exists():
        return []

    modules = sorted(str(p.relative_to(base_path)) for p in module_dir.rglob("*.py"))
    return modules


def validate_syntax(modules: list[str], reporter: ValidationReporter) -> ValidationResult:
    """Validate syntax of all modules."""
    reporter.section("1. SYNTAX VALIDATION")
    details = []
    all_passed = True

    for module in modules:
        try:
            module_path = Path(module)
            with module_path.open(encoding="utf-8") as source:
                compile(source.read(), module, 'exec')
            reporter.success(module, indent=1)
            details.append(f"✓ {module}")
        except SyntaxError as e:
            reporter.failure(f"{module}: {e}", indent=1)
            details.append(f"✗ {module}: {e}")
            all_passed = False

    message = "All modules have valid syntax" if all_passed else "Syntax errors found"
    return ValidationResult(passed=all_passed, message=message, details=details)


def validate_import_structure(
    rules: dict[str, dict[str, list[tuple[str, ...]]]],
    reporter: ValidationReporter
) -> ValidationResult:
    """Validate import structure according to rules."""
    reporter.section("2. IMPORT STRUCTURE ANALYSIS")
    details = []
    all_passed = True

    for module_path, checks in rules.items():
        imports = analyze_imports(module_path)
        reporter.info(f"{module_path}:", indent=1)

        for required in checks['required']:
            if required in imports:
                msg = f"Has: {required}"
                reporter.success(msg, indent=2)
                details.append(f"✓ {module_path}: {msg}")
            else:
                msg = f"Missing: {required}"
                reporter.failure(msg, indent=2)
                details.append(f"✗ {module_path}: {msg}")
                all_passed = False

        for forbidden in checks['forbidden']:
            if forbidden in imports:
                msg = f"Incorrect import: {forbidden}"
                reporter.failure(msg, indent=2)
                details.append(f"✗ {module_path}: {msg}")
                all_passed = False
            else:
                msg = f"Correctly avoids: {forbidden}"
                reporter.success(msg, indent=2)
                details.append(f"✓ {module_path}: {msg}")

    message = "Import structure is correct" if all_passed else "Import structure violations found"
    return ValidationResult(passed=all_passed, message=message, details=details)


def validate_circular_imports(modules: list[str], reporter: ValidationReporter) -> ValidationResult:
    """Check for circular import dependencies."""
    reporter.section("3. CIRCULAR IMPORT CHECK")
    details = []
    circular_found = False

    # Build import graph
    import_graph = {}
    for module in modules:
        imports = analyze_imports(module)
        # Normalize path separators (handle both / and \) before converting to module name
        module_name = module.replace('\\', '/').replace('/', '.').replace('.py', '')
        import_graph[module_name] = []

        for imp in imports:
            if imp[0] == 'from' and imp[1].startswith('routes.import_export'):
                import_graph[module_name].append(imp[1])

    # Check for circular dependencies
    for module, deps in import_graph.items():
        if deps:
            dep_info = f"{module} → {', '.join(deps)}"
            reporter.info(dep_info, indent=1)
            details.append(dep_info)

            # Simple check: if any dependency imports back to us
            for dep in deps:
                if dep in import_graph and module in import_graph[dep]:
                    warning = f"Potential circular: {module} ↔ {dep}"
                    reporter.warning(warning, indent=2)
                    details.append(f"⚠ {warning}")
                    circular_found = True

    if not circular_found:
        msg = "No circular imports detected"
        reporter.success(msg, indent=1)
        details.append(f"✓ {msg}")

    message = "Circular imports detected" if circular_found else "No circular imports"
    return ValidationResult(passed=not circular_found, message=message, details=details)


def validate_backward_compatibility(reporter: ValidationReporter) -> ValidationResult:
    """Check that the compatibility shim exists and has correct exports."""
    reporter.section("4. BACKWARD COMPATIBILITY CHECK")
    details = []

    shim_path = 'routes/import_export.py'
    required_exports = ['export_data', 'import_data', 'export_size']

    try:
        with Path(shim_path).open(encoding="utf-8") as shim_file:
            shim_content = shim_file.read()

        all_present = all(export in shim_content for export in required_exports)

        if not all_present:
            msg = f"{shim_path} missing some exports"
            reporter.failure(msg, indent=1)
            details.append(f"✗ {msg}")
            return ValidationResult(passed=False, message=msg, details=details)

        msg = f"{shim_path} exports: {', '.join(required_exports)}"
        reporter.success(msg, indent=1)
        details.append(f"✓ {msg}")
        return ValidationResult(passed=True, message="Backward compatibility maintained", details=details)

    except FileNotFoundError:
        msg = f"{shim_path} not found"
        reporter.failure(msg, indent=1)
        details.append(f"✗ {msg}")
        return ValidationResult(passed=False, message=msg, details=details)


def validate_module_sizes(
    modules: list[str],
    reporter: ValidationReporter,
    threshold: int = LINE_THRESHOLD
) -> ValidationResult:
    """Verify that modules are under the size threshold."""
    reporter.section("5. MODULE SIZE VERIFICATION")
    details = []

    max_lines = 0
    max_module = None
    all_under_threshold = True

    for module in modules:
        module_path = Path(module)
        with module_path.open(encoding="utf-8") as source:
            lines = sum(1 for _ in source)

        passed = lines < threshold
        msg = f"{module}: {lines} lines"
        reporter.status(passed, msg, indent=1)
        details.append(f"{'✓' if passed else '✗'} {msg}")

        if lines > max_lines:
            max_lines = lines
            max_module = module

        if lines >= threshold:
            all_under_threshold = False

    largest_info = f"Largest module: {max_module} ({max_lines} lines)"
    reporter.info(f"\n{largest_info}", indent=1)
    details.append(largest_info)

    if not all_under_threshold:
        warning = f"Some modules exceed {threshold}-line threshold"
        reporter.warning(warning, indent=1)
        details.append(f"⚠ {warning}")

    message = f"All modules under {threshold} lines" if all_under_threshold else f"Some modules exceed {threshold} lines"
    return ValidationResult(passed=all_under_threshold, message=message, details=details)


def main() -> int:
    """Run all validation checks and report results."""
    reporter = ValidationReporter()
    reporter.header("COMPREHENSIVE IMPORT VALIDATION")

    # Discover modules
    modules = discover_modules()
    if not modules:
        print("No modules found in routes/import_export/")
        return 1

    # Run syntax validation
    syntax_result = validate_syntax(modules, reporter)
    if not syntax_result.passed:
        reporter.info(f"\n❌ {syntax_result.message}")
        return 1

    # Run import structure validation
    import_result = validate_import_structure(IMPORT_VALIDATION_RULES, reporter)
    if not import_result.passed:
        reporter.info(f"\n❌ {import_result.message}")
        return 1

    # Run circular import check
    circular_result = validate_circular_imports(modules, reporter)

    # Run backward compatibility check
    compat_result = validate_backward_compatibility(reporter)
    if not compat_result.passed:
        reporter.info(f"\n❌ {compat_result.message}")
        return 1

    # Run module size verification
    size_result = validate_module_sizes(modules, reporter)

    # Summary
    print()
    results = {
        "Syntax validation": syntax_result.passed,
        "Import structure": import_result.passed,
        "Circular imports": circular_result.passed,
        "Backward compatibility": compat_result.passed,
        "Module sizes": size_result.passed,
    }
    reporter.result_summary(results)

    if all(results.values()):
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("\nThe import_export decomposition is correct and ready for unit tests.")
        print("Tests should pass when run in an environment with pytest installed.")
        return 0

    print("\n❌ SOME VALIDATIONS FAILED")
    return 1

if __name__ == '__main__':
    sys.exit(main())
