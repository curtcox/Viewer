# Instructions for Running Unit Tests

## Prerequisites

### 1. Install Dependencies

The required dependencies are already in `requirements.txt`, but key packages needed for testing:
- pytest (test runner)
- flask (web framework)
- logfire (logging/telemetry)
- All other packages in requirements.txt

To install:
```bash
pip install -q logfire aiohttp attrs flask flask-sqlalchemy flask-login flask-wtf wtforms sqlalchemy werkzeug
```

Note: You may encounter a `blinker` conflict from Debian packages. This can be ignored - the system will work despite the warning.

### 2. Set Environment Variables

Tests require these environment variables (automatically set by test-unit script):
```bash
export DATABASE_URL="sqlite:///:memory:"
export SESSION_SECRET="test-secret-key"
export TESTING="True"
```

The `test-unit` script (at repository root) handles this automatically via `tests/test_support.py`.

## Running Tests

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

### Useful pytest Flags
- `-v` - Verbose output (show test names)
- `-x` - Stop on first failure
- `-s` - Show print statements (don't capture output)
- `-xvs` - Combination: stop on first failure, verbose, show output
- `--tb=short` - Shorter tracebacks
- `-k PATTERN` - Run tests matching pattern

### See Pass/Fail Summary
```bash
./test-unit -- tests/test_import_export.py -v 2>&1 | grep -E "PASSED|FAILED"
```

## Test Infrastructure

### Key Files
- `test-unit` - Main test runner script at repository root
- `tests/test_support.py` - Test environment configuration
- `pytest.ini` - Pytest configuration

### Test Environment Setup
The `test-unit` script automatically:
1. Sets environment variables (DATABASE_URL, SESSION_SECRET, TESTING)
2. Configures PYTHONPATH to include repository root, step_impl, and tests directories
3. Uses in-memory SQLite database for isolation

### Test Database
- Each test class creates a fresh database in setUp()
- Uses in-memory SQLite (`:memory:`) for speed
- Automatically cleaned up after tests

## Debugging Tests

### Run a Test with Python Debugger
```bash
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase::test_specific_test -xvs --pdb
```

### Check What's in Test Database
Create a debug script like this:
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
        # inspect records
        pass
```

### Patch Functions for Debugging
```python
import routes.import_export as ie

original_func = ie._some_function

def debug_func(*args, **kwargs):
    print(f"Called with: {args}, {kwargs}")
    result = original_func(*args, **kwargs)
    print(f"Returned: {result}")
    return result

ie._some_function = debug_func
```

## Common Issues

### ModuleNotFoundError: No module named 'logfire'
**Solution**: Install logfire: `pip install -q logfire`

### ModuleNotFoundError: No module named 'flask'
**Solution**: Install Flask and dependencies: `pip install -q flask flask-sqlalchemy flask-login`

### Cannot uninstall blinker
**Solution**: This is expected due to Debian system packages. Use `--ignore-installed` if needed, or just ignore the warning.

### Tests fail with "Logfire is not enabled"
**Solution**: This is just a warning, not an error. Tests will run fine.

## Test File Structure

### Unit Tests
- `tests/test_import_export.py` - Import/export functionality tests
- `tests/test_*.py` - Other unit test files

### Integration Tests
- `tests/integration/test_*.py` - Integration tests
- Run with: `./test-unit -- tests/integration/ -v`

### Property Tests
- `tests/property/` - Hypothesis property-based tests

### BDD Tests (Gauge)
- `specs/*.spec` - Gauge specification files
- `step_impl/*_steps.py` - Step implementations
- Run with: `./test-gauge`

## CI Environment

The CI uses a Docker image: `ghcr.io/curtcox/viewer-ci:latest`

CI runs:
1. Ruff (linter)
2. Pylint (errors only)
3. Mypy (type checker)
4. Unit tests with coverage
5. Integration tests
6. Property tests
7. Gauge specs (BDD tests)

All must pass for PR to merge.

## Quick Reference

```bash
# Run single test with full output
./test-unit -- tests/test_import_export.py::ImportExportRoutesTestCase::test_name -xvs

# Run all import/export tests and show summary
./test-unit -- tests/test_import_export.py -v 2>&1 | grep -E "PASSED|FAILED" | head -60

# Run tests and stop on first failure
./test-unit -- tests/test_import_export.py -x

# Run tests matching a pattern
./test-unit -- tests/test_import_export.py -k "export_cid" -v

# Run with coverage
./test-unit --coverage -- tests/test_import_export.py

# Check test count
./test-unit -- tests/test_import_export.py --collect-only | grep "test_"
```
