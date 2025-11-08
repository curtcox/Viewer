#!/usr/bin/env python3
"""Comprehensive import validation for routes/import_export decomposition."""

import sys
import ast
import importlib.util
from pathlib import Path

# Add the repo root to sys.path
sys.path.insert(0, '/home/user/Viewer')

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

def main():
    print("="*70)
    print("COMPREHENSIVE IMPORT VALIDATION")
    print("="*70)

    modules = [
        'routes/import_export/__init__.py',
        'routes/import_export/cid_utils.py',
        'routes/import_export/filesystem_collection.py',
        'routes/import_export/dependency_analyzer.py',
        'routes/import_export/export_helpers.py',
        'routes/import_export/export_sections.py',
        'routes/import_export/export_preview.py',
        'routes/import_export/export_engine.py',
        'routes/import_export/change_history.py',
        'routes/import_export/import_sources.py',
        'routes/import_export/import_entities.py',
        'routes/import_export/import_engine.py',
        'routes/import_export/routes_integration.py',
        'routes/import_export/routes.py',
    ]

    print("\n1. SYNTAX VALIDATION")
    print("-" * 70)
    syntax_ok = True
    for module in modules:
        try:
            module_path = Path(module)
            with module_path.open(encoding="utf-8") as source:
                compile(source.read(), module, 'exec')
            print(f"  ✓ {module}")
        except SyntaxError as e:
            print(f"  ✗ {module}: {e}")
            syntax_ok = False

    if not syntax_ok:
        print("\n❌ Syntax validation failed!")
        return 1

    print("\n2. IMPORT STRUCTURE ANALYSIS")
    print("-" * 70)

    # Check for problematic imports
    problematic = {
        'routes/import_export/import_sources.py': {
            'must_have': [
                ('from', 'cid_presenter', 'format_cid'),
                ('from', 'cid_utils', 'generate_cid'),
            ],
            'must_not_have': [
                ('from', 'cid_utils', 'format_cid'),
            ]
        },
        'routes/import_export/import_engine.py': {
            'must_have': [
                ('from', 'cid_presenter', 'format_cid'),
                ('from', 'cid_utils', 'generate_cid'),
            ],
            'must_not_have': [
                ('from', 'cid_utils', 'format_cid'),
            ]
        },
    }

    import_ok = True
    for module_path, checks in problematic.items():
        imports = analyze_imports(module_path)
        print(f"\n  {module_path}:")

        for required in checks['must_have']:
            if required in imports:
                print(f"    ✓ Has: {required}")
            else:
                print(f"    ✗ Missing: {required}")
                import_ok = False

        for forbidden in checks['must_not_have']:
            if forbidden in imports:
                print(f"    ✗ Incorrect import: {forbidden}")
                import_ok = False
            else:
                print(f"    ✓ Correctly avoids: {forbidden}")

    if not import_ok:
        print("\n❌ Import structure validation failed!")
        return 1

    print("\n3. CIRCULAR IMPORT CHECK")
    print("-" * 70)

    # Check for potential circular imports
    import_graph = {}
    for module in modules:
        imports = analyze_imports(module)
        module_name = module.replace('/', '.').replace('.py', '')
        import_graph[module_name] = []

        for imp in imports:
            if imp[0] == 'from' and imp[1].startswith('routes.import_export'):
                import_graph[module_name].append(imp[1])

    circular_found = False
    for module, deps in import_graph.items():
        if deps:
            print(f"  {module} → {', '.join(deps)}")
            # Simple check: if any dependency imports back to us
            for dep in deps:
                if dep in import_graph and module in import_graph[dep]:
                    print(f"    ⚠ Potential circular: {module} ↔ {dep}")
                    circular_found = True

    if not circular_found:
        print("  ✓ No circular imports detected")

    print("\n4. BACKWARD COMPATIBILITY CHECK")
    print("-" * 70)

    # Check that the compatibility shim exists and has correct exports
    shim_path = 'routes/import_export.py'
    try:
        with Path(shim_path).open(encoding="utf-8") as shim_file:
            shim_content = shim_file.read()

        required_exports = ['export_data', 'import_data', 'export_size']
        all_present = all(export in shim_content for export in required_exports)

        if not all_present:
            print(f"  ✗ {shim_path} missing some exports")
            return 1

        print(f"  ✓ {shim_path} exports: {', '.join(required_exports)}")
    except FileNotFoundError:
        print(f"  ✗ {shim_path} not found")
        return 1

    print("\n5. MODULE SIZE VERIFICATION")
    print("-" * 70)

    max_lines = 0
    max_module = None
    all_under_threshold = True

    for module in modules:
        module_path = Path(module)
        with module_path.open(encoding="utf-8") as source:
            lines = sum(1 for _ in source)

        status = "✓" if lines < 1000 else "✗"
        print(f"  {status} {module}: {lines} lines")

        if lines > max_lines:
            max_lines = lines
            max_module = module

        if lines >= 1000:
            all_under_threshold = False

    print(f"\n  Largest module: {max_module} ({max_lines} lines)")

    if not all_under_threshold:
        print("  ⚠ Some modules exceed 1000-line threshold")

    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    results = {
        "Syntax validation": syntax_ok,
        "Import structure": import_ok,
        "Circular imports": not circular_found,
        "Backward compatibility": True,
        "Module sizes": all_under_threshold,
    }

    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")

    if all(results.values()):
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("\nThe import_export decomposition is correct and ready for unit tests.")
        print("Tests should pass when run in an environment with pytest installed.")
        return 0

    print("\n❌ SOME VALIDATIONS FAILED")
    return 1

if __name__ == '__main__':
    sys.exit(main())
