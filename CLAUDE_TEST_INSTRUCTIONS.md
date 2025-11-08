# Instructions for Running Unit Tests

## 🚀 Quick Start - Run This First!

**Always use the provided test runner scripts - they handle environment setup automatically:**

```bash
# Run all unit tests quickly (recommended)
./scripts/checks/run_unit_tests_quick.sh

# Or use the main test runner directly
./test-unit -- --maxfail=1 -q

# Run specific test file
./test-unit -- tests/test_import_export.py -v
```

**Important:** The `test-unit` script automatically sets up the environment (DATABASE_URL, SESSION_SECRET, TESTING variables and PYTHONPATH). You don't need to set these manually!

## 🔍 If pytest is Not Available

If you encounter `No module named pytest`, you have two options:

### Option 1: Use the Validation Script (Recommended for Code Changes)

For module decomposition and import fixes, use the comprehensive validation script:

```bash
python3 validate_import_export.py
```

This validates:
- Python syntax compilation
- Import structure correctness
- Circular import detection
- Backward compatibility
- Module sizes

### Option 2: Install Dependencies

If you need to run actual unit tests:

```bash
# Use the install script (recommended)
./install

# Or install directly
pip install -r requirements.txt
```

**Note:** The CI environment always has pytest installed. Local validation ensures code is correct before CI runs.

## 📋 Prerequisites

### Required Dependencies

All dependencies are in `requirements.txt` and `pyproject.toml`. Key testing packages:
- **pytest** - Test runner
- **pytest-cov** - Coverage reporting
- **pytest-testmon** - Smart test selection
- **hypothesis** - Property-based testing
- **flask** and related packages - Web framework

### Auto-Configured Environment Variables

The `test-unit` script automatically sets:
```bash
DATABASE_URL="sqlite:///:memory:"
SESSION_SECRET="test-secret-key"
TESTING="True"
```

You **don't need** to set these manually. The script handles it via `tests/test_support.py`.

## 🎯 Running Tests

### Run All Tests Quickly
```bash
./scripts/checks/run_unit_tests_quick.sh
```

This runs all unit tests with `--maxfail=1` (stops on first failure) and quiet output.

### Run All Tests in a File
```bash
./test-unit -- tests/test_import_export.py -v
```

### Run a Specific Test Class
```bash
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase -v
```

### Run a Single Test Method
```bash
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_selected_collections -xvs
```

### Run Tests Matching a Pattern
```bash
./test-unit -- -k "export_cid" -v
./test-unit -- -k "import" -v
./test-unit -- -k "alias or server" -v
```

### Useful pytest Flags
- `-v` - Verbose output (show test names)
- `-x` - Stop on first failure
- `-s` - Show print statements (don't capture output)
- `-xvs` - Combination: stop on first failure, verbose, show output
- `--tb=short` - Shorter tracebacks
- `--tb=no` - No traceback
- `-q` - Quiet mode (minimal output)
- `--maxfail=N` - Stop after N failures
- `-k PATTERN` - Run tests matching pattern
- `--collect-only` - Show what tests would run without running them

### See Pass/Fail Summary
```bash
./test-unit -- tests/test_import_export.py -v 2>&1 | grep -E "PASSED|FAILED"
```

## 🏗️ Test Infrastructure

### Key Files
- `test-unit` - Main test runner script (Python-based, at repository root)
- `scripts/checks/run_unit_tests_quick.sh` - Quick test runner (Bash wrapper)
- `tests/test_support.py` - Test environment configuration
- `pytest.ini` - Pytest configuration (if present)
- `pyproject.toml` - Project configuration including test dependencies

### Test Environment Setup
The `test-unit` script automatically:
1. Sets environment variables (DATABASE_URL, SESSION_SECRET, TESTING)
2. Configures PYTHONPATH to include repository root, step_impl, and tests directories
3. Uses in-memory SQLite database for isolation
4. Imports `tests.test_support` to build test environment

### Test Database
- Each test class creates a fresh database in `setUp()`
- Uses in-memory SQLite (`:memory:`) for speed and isolation
- Automatically cleaned up after tests
- No persistent state between test runs

## 🐛 Debugging Tests

### Run a Test with Python Debugger
```bash
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase::test_specific_test -xvs --pdb
```

### Show Output During Tests
```bash
./test-unit -- tests/test_import_export.py -s
```

This shows `print()` statements and other output during test execution.

### Check Test Collection (Dry Run)
```bash
./test-unit -- tests/test_import_export.py --collect-only
```

Shows what tests would run without actually running them.

### Run with Full Traceback
```bash
./test-unit -- tests/test_import_export.py --tb=long
```

### Check What's in Test Database
Create a debug script:
```python
import sys
sys.path.insert(0, '/home/user/Viewer')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'True'

from tests.test_import_export import ImportExportRoutesTestCase
from models import CID
import json

test = ImportExportRoutesTestCase('test_name')
test.setUp()

# ... setup test data ...

with test.app.app_context():
    all_records = CID.query.all()
    for record in all_records:
        print(f"CID: {record.path}, size: {len(record.file_data or b'')}")
```

### Patch Functions for Debugging
```python
# For decomposed modules, import from the package
from routes.import_export import export_engine

original_func = export_engine.build_export_payload

def debug_func(*args, **kwargs):
    print(f"Called with: {args}, {kwargs}")
    result = original_func(*args, **kwargs)
    print(f"Returned: {result}")
    return result

export_engine.build_export_payload = debug_func
```

## ⚠️ Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'pytest'`

**Solution**: Install dependencies using one of these methods:
```bash
# Option 1: Use install script (recommended)
./install

# Option 2: Direct install
pip install -r requirements.txt

# Option 3: Quick install of just pytest
pip install pytest pytest-cov
```

### Issue: `ModuleNotFoundError: No module named 'logfire'`

**Solution**: Install logfire and related packages:
```bash
pip install logfire aiohttp attrs
```

### Issue: `ModuleNotFoundError: No module named 'flask'`

**Solution**: Install Flask stack:
```bash
pip install flask flask-sqlalchemy flask-login flask-wtf wtforms sqlalchemy werkzeug
```

### Issue: `ImportError: cannot import name 'format_cid' from 'cid_utils'`

**Solution**: This was fixed in commit 62516a8. Make sure you have the latest code:
- `format_cid` should be imported from `cid_presenter` (not `cid_utils`)
- `generate_cid` should be imported from `cid_utils`

To verify the fix is present:
```bash
python3 validate_import_export.py
```

### Issue: Cannot uninstall blinker

**Solution**: This is expected due to Debian system packages. Safe to ignore or use:
```bash
pip install --ignore-installed blinker
```

### Issue: Tests fail with "Logfire is not enabled"

**Solution**: This is just a warning, not an error. Tests will run fine. Logfire is for production observability.

### Issue: Test collection fails

**Solution**: Check for import errors in test files:
```bash
./test-unit -- --collect-only tests/test_import_export.py
```

If this fails, there's likely an import error in the module code or test file.

## 📁 Test File Structure

### Unit Tests (`tests/`)
- `tests/test_import_export.py` - Import/export functionality tests
- `tests/test_server_execution.py` - Server execution tests
- `tests/test_*.py` - Other unit test files
- Uses unittest.TestCase pattern with setUp/tearDown

### Integration Tests (`tests/integration/`)
- `tests/integration/test_*.py` - Integration tests
- Test multiple components working together
- Run with: `./test-unit -- tests/integration/ -v`

### Property Tests (`tests/property/`)
- Uses Hypothesis for property-based testing
- Tests invariants and edge cases
- Run with: `./test-unit -- tests/property/ -v`

### BDD Tests (Gauge) (`specs/`)
- `specs/*.spec` - Gauge specification files (Gherkin-like syntax)
- `step_impl/*_steps.py` - Step implementations
- Run with: `./test-gauge`

## 🔄 After Module Decomposition

When a module has been decomposed (like routes/import_export.py → routes/import_export/):

### 1. Run Validation First
```bash
python3 validate_import_export.py
```

This checks:
- ✅ All modules compile (syntax validation)
- ✅ Import structure is correct
- ✅ No circular imports
- ✅ Backward compatibility maintained
- ✅ Module sizes under threshold

### 2. Then Run Unit Tests
```bash
./test-unit -- tests/test_import_export.py -v
```

### 3. Check Test Coverage
```bash
./test-unit --coverage -- tests/test_import_export.py
```

### 4. Update Test Imports if Needed

If you need to test internal functions from decomposed modules:
```python
# Old way (single file)
from routes.import_export import _some_internal_function

# New way (decomposed package)
from routes.import_export.export_engine import some_internal_function
from routes.import_export.import_entities import import_aliases_with_names
```

But prefer testing through public API when possible:
```python
from routes.import_export import export_data, import_data, export_size
```

## 🏭 CI Environment

The CI uses a Docker image: `ghcr.io/curtcox/viewer-ci:latest`

### CI Test Pipeline
1. **Ruff** - Fast Python linter
2. **Pylint** - Comprehensive linting (errors only in CI)
3. **Mypy** - Static type checking
4. **Unit tests with coverage** - All tests must pass
5. **Integration tests** - Multi-component tests
6. **Property tests** - Hypothesis tests
7. **Gauge specs** - BDD acceptance tests

All checks must pass for PR to merge.

### Replicating CI Locally
```bash
# Run checks in CI order
ruff check .
pylint --errors-only routes/ *.py
mypy --config-file pyproject.toml .
./test-unit -- --cov=. --cov-report=term
./test-gauge
```

## 📚 Quick Reference Cheat Sheet

```bash
# ============================================
# MOST COMMON COMMANDS
# ============================================

# Run all unit tests quickly (use this!)
./scripts/checks/run_unit_tests_quick.sh

# Run single test with full output
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase::test_name -xvs

# Run all tests in a file
./test-unit -- tests/test_import_export.py -v

# ============================================
# VALIDATION (when pytest not available)
# ============================================

# Validate decomposed import_export modules
python3 validate_import_export.py

# Check Python syntax manually
python3 -m py_compile routes/import_export/*.py

# ============================================
# DEBUGGING
# ============================================

# Stop on first failure, show output
./test-unit -- tests/test_import_export.py -xvs

# Run with debugger
./test-unit -- tests/test_import_export.py::ClassName::test_name --pdb

# See what tests would run
./test-unit -- tests/test_import_export.py --collect-only

# ============================================
# FILTERING
# ============================================

# Run tests matching pattern
./test-unit -- -k "export_cid" -v
./test-unit -- -k "import" -v

# Run specific test class
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase -v

# ============================================
# COVERAGE
# ============================================

# Run with coverage report
./test-unit --coverage -- tests/test_import_export.py

# Coverage for specific module
./test-unit --coverage -- tests/test_import_export.py --cov=routes.import_export

# ============================================
# OUTPUT CONTROL
# ============================================

# Quiet mode (minimal output)
./test-unit -- tests/test_import_export.py -q

# Show pass/fail summary only
./test-unit -- tests/test_import_export.py -v 2>&1 | grep -E "PASSED|FAILED"

# No traceback, just pass/fail
./test-unit -- tests/test_import_export.py --tb=no

# ============================================
# INSTALLATION
# ============================================

# Install all dependencies
./install

# Or manually
pip install -r requirements.txt
```

## 💡 Pro Tips

### 1. Always Run Tests After Changes
Make it a habit to run tests after any code changes:
```bash
./scripts/checks/run_unit_tests_quick.sh
```

### 2. Use Pattern Matching to Speed Up Testing
When working on specific functionality:
```bash
./test-unit -- -k "export" -v  # Only export tests
./test-unit -- -k "import" -v  # Only import tests
```

### 3. Use Validation Scripts for Quick Feedback
When refactoring (especially decomposing modules):
```bash
python3 validate_import_export.py  # Faster than full test run
```

### 4. Stop on First Failure for Fast Feedback
```bash
./test-unit -- tests/test_import_export.py -x
```

### 5. Check Test Collection Before Running
```bash
./test-unit -- --collect-only | wc -l  # Count tests
./test-unit -- --collect-only | grep "test_export"  # Find specific tests
```

### 6. Use Verbose Mode to Understand Test Flow
```bash
./test-unit -- tests/test_import_export.py::ClassName::test_name -xvs
```

The flags mean:
- `-x` = stop on first failure
- `-v` = verbose (show test names)
- `-s` = show output (don't capture)

## 🎯 For Claude: When to Run Tests

**ALWAYS run tests in these situations:**

1. ✅ After fixing bugs or errors
2. ✅ After refactoring code
3. ✅ After decomposing modules
4. ✅ After changing imports
5. ✅ After adding new functionality
6. ✅ Before committing changes
7. ✅ When user explicitly asks

**If pytest is not available:**
1. ✅ Use `python3 validate_import_export.py` for import_export changes
2. ✅ Run Python syntax checks
3. ✅ Document that full tests should run in CI

**Never hesitate to run tests!** The scripts handle environment setup automatically.

## 📖 Additional Resources

- **Test Support Module**: `tests/test_support.py` - Environment setup logic
- **Main Test Runner**: `test-unit` - Wraps pytest with environment configuration
- **Quick Test Script**: `scripts/checks/run_unit_tests_quick.sh` - Fast test runner
- **Validation Script**: `validate_import_export.py` - Import/syntax validation for decomposed modules

For more details on specific test patterns or fixtures, see the test files themselves or `tests/test_support.py`.
