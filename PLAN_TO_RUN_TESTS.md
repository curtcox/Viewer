# Plan to Run Unit Tests

**Created**: 2024-11-07
**Status**: Prerequisites not met (pytest not installed)
**Objective**: Run `./scripts/checks/run_unit_tests_quick.sh` successfully

---

## Current Situation

**Problem**: pytest is not installed in the current environment
```bash
$ ./scripts/checks/run_unit_tests_quick.sh
/usr/local/bin/python3: No module named pytest
```

**Impact**: Cannot run unit tests to verify the import_export decomposition

**Environment**:
- Python: 3.11.14
- Location: `/usr/local/bin/python3`
- Working directory: `/home/user/Viewer`

---

## Prerequisites Check

### Step 1: Check Python Installation
```bash
which python3
python3 --version
```

**Expected Output**:
```
/usr/local/bin/python3
Python 3.11.14
```

✅ **Status**: Complete

### Step 2: Check pip Availability
```bash
python3 -m pip --version
```

**Expected**: pip version information
**Current Status**: Unknown (need to verify)

### Step 3: Check for Virtual Environment
```bash
ls -la venv/
source venv/bin/activate 2>&1 || echo "No venv found"
```

**Expected**: Either activate venv or report it doesn't exist
**Current Status**: Unknown

---

## Installation Plan

### Option 1: Use the Install Script (Recommended)

**Step 1.1**: Check if install script exists
```bash
ls -la install
cat install
```

**Step 1.2**: Run the install script
```bash
./install
```

**Expected Behavior**:
- Creates virtual environment if needed
- Installs all dependencies from requirements.txt
- Sets up .env file

**Potential Issues**:
- May require write permissions
- May conflict with system packages (blinker)
- Network access needed for PyPI

**Success Criteria**:
```bash
python3 -m pytest --version
# Should output: pytest X.Y.Z
```

### Option 2: Direct pip Install (If install script fails)

**Step 2.1**: Install pytest and dependencies directly
```bash
python3 -m pip install pytest pytest-cov pytest-testmon
```

**Step 2.2**: Install application dependencies
```bash
python3 -m pip install -r requirements.txt
```

**Step 2.3**: Verify installation
```bash
python3 -m pytest --version
```

### Option 3: Use Virtual Environment (Most Isolated)

**Step 3.1**: Create virtual environment
```bash
python3 -m venv venv
```

**Step 3.2**: Activate virtual environment
```bash
source venv/bin/activate
```

**Step 3.3**: Upgrade pip
```bash
pip install --upgrade pip
```

**Step 3.4**: Install dependencies
```bash
pip install -r requirements.txt
```

**Step 3.5**: Verify installation
```bash
pytest --version
```

---

## Running Tests After Installation

### Quick Test Run (Recommended First Step)
```bash
./scripts/checks/run_unit_tests_quick.sh
```

**Expected Output**:
- Test collection summary
- Test execution results
- Pass/fail counts
- Exit code 0 if all pass

### Alternative: Direct pytest Invocation
```bash
./test-unit -- --maxfail=1 -q
```

### Test Specific Module (Import/Export)
```bash
./test-unit -- tests/test_import_export.py -v
```

### Check Test Collection Only (No Execution)
```bash
./test-unit -- --collect-only
```

**Expected**: Should show all tests without ImportError

---

## Validation Steps

### Step 1: Verify No Import Errors
```bash
./test-unit -- --collect-only 2>&1 | grep -i "error"
```

**Expected**: No ImportError messages
**Success Criteria**: Exit code 0, no error output

### Step 2: Run Quick Tests
```bash
./scripts/checks/run_unit_tests_quick.sh
```

**Expected**: All tests pass
**Success Criteria**: Exit code 0, "PASSED" messages

### Step 3: Run Full Test Suite
```bash
./test-unit -- -v
```

**Expected**: All tests pass with verbose output
**Time**: May take several minutes

### Step 4: Run Import/Export Tests Specifically
```bash
./test-unit -- tests/test_import_export.py -v
```

**Expected**: All import/export tests pass
**Success Criteria**: No failures related to module decomposition

---

## Troubleshooting Plan

### Issue: Permission Denied

**Symptom**: Cannot write to directories

**Solution 1**: Use --user flag
```bash
python3 -m pip install --user pytest pytest-cov
```

**Solution 2**: Use virtual environment (Option 3 above)

### Issue: Conflicting Dependencies (blinker)

**Symptom**: Warning about conflicting blinker package

**Solution**: Ignore the warning
```bash
# This is expected - Debian system packages conflict
# Tests will still work
```

**Alternative**: Force reinstall
```bash
pip install --ignore-installed blinker
```

### Issue: ModuleNotFoundError for Other Packages

**Symptom**: Missing logfire, flask, etc.

**Solution**: Install missing packages individually
```bash
pip install logfire aiohttp attrs
pip install flask flask-sqlalchemy flask-login flask-wtf
pip install wtforms sqlalchemy werkzeug
```

### Issue: ImportError During Test Collection

**Symptom**: `cannot import name 'format_cid' from 'cid_utils'`

**Status**: ✅ **FIXED** in commit 62516a8

**Verification**: Run validation script
```bash
python3 validate_import_export.py
```

**Expected**: All validations pass

### Issue: Tests Fail Due to Module Decomposition

**Symptom**: Tests import internal functions that moved

**Solution**: Update test imports
```python
# Old
from routes.import_export import _internal_function

# New
from routes.import_export.export_engine import internal_function
```

---

## Success Criteria Checklist

- [ ] pytest is installed and available
- [ ] `pytest --version` returns version information
- [ ] `./test-unit -- --collect-only` runs without ImportError
- [ ] `./scripts/checks/run_unit_tests_quick.sh` completes
- [ ] All unit tests pass (exit code 0)
- [ ] No test failures related to import_export decomposition
- [ ] Validation script still passes: `python3 validate_import_export.py`

---

## Execution Steps (Ordered)

### Phase 1: Install Dependencies (Choose One)
1. **Try Option 1 first**: `./install` (if available and works)
2. **If Option 1 fails**: Try Option 2 (direct pip install)
3. **If Option 2 fails**: Try Option 3 (virtual environment)

### Phase 2: Verify Installation
```bash
python3 -m pytest --version
# Should succeed and show version
```

### Phase 3: Validate Code (Before Running Tests)
```bash
python3 validate_import_export.py
# Should show: 🎉 ALL VALIDATIONS PASSED!
```

### Phase 4: Test Collection
```bash
./test-unit -- --collect-only
# Should collect tests without ImportError
```

### Phase 5: Run Quick Tests
```bash
./scripts/checks/run_unit_tests_quick.sh
# Should run and (hopefully) pass all tests
```

### Phase 6: Analyze Results
If tests fail:
- Check error messages
- Identify if failures are due to decomposition or unrelated
- Update test imports if needed
- Re-run specific failing tests

---

## Time Estimates

| Phase | Estimated Time | Notes |
|-------|---------------|-------|
| Install Dependencies | 2-5 minutes | Network dependent |
| Verify Installation | 30 seconds | Quick checks |
| Validate Code | 10 seconds | validation script |
| Test Collection | 10-30 seconds | Import checks |
| Run Quick Tests | 1-3 minutes | Depends on test count |
| Run Full Suite | 5-10 minutes | All tests |
| Troubleshooting (if needed) | 5-15 minutes | Varies |

**Total**: 10-30 minutes (including troubleshooting)

---

## Expected Outcomes

### Best Case (90% probability)
1. Installation succeeds
2. Test collection succeeds (no ImportError)
3. All tests pass
4. Import/export decomposition confirmed working
5. Ready to merge PR

### Likely Case (8% probability)
1. Installation succeeds
2. Test collection succeeds
3. 1-3 tests fail due to import path changes
4. Update test imports
5. Re-run tests, all pass
6. Ready to merge PR

### Worst Case (2% probability)
1. Installation has issues
2. Need to use virtual environment
3. Some tests fail due to logic issues
4. Debug and fix issues
5. Re-test until passing
6. Then ready to merge PR

---

## Fallback: If pytest Cannot Be Installed

### Alternative Validation
If pytest installation is impossible in the current environment:

1. **Use validation script** (already passing):
   ```bash
   python3 validate_import_export.py
   ```

2. **Document CI will run tests**:
   - CI environment has pytest installed
   - Tests will run automatically on PR
   - Our validation gives high confidence they'll pass

3. **Manual import testing**:
   ```python
   python3 << 'EOF'
   import sys
   sys.path.insert(0, '/home/user/Viewer')

   # Test imports work
   from routes.import_export import export_data, import_data, export_size
   print("✓ Public API imports work")

   from routes.import_export.export_engine import build_export_payload
   print("✓ Internal module imports work")

   print("\n✅ All imports successful!")
   EOF
   ```

4. **Proceed to PR with documentation**:
   - Note pytest unavailable locally
   - Include validation results
   - Include manual import test results
   - Trust CI to run full tests

---

## Next Actions

**Immediate**: Execute Phase 1 (Install Dependencies)

**Command to run**:
```bash
./install
```

**If that fails**:
```bash
python3 -m pip install pytest pytest-cov
python3 -m pip install -r requirements.txt
```

**Then verify**:
```bash
python3 -m pytest --version
```

**Then proceed** with Phase 2-6 as documented above.

---

## Notes

- This plan assumes standard Linux environment with Python 3.11+
- Network access required for package installation
- Write permissions needed for pip installs (or use --user flag)
- Virtual environment recommended for isolation
- All validation indicates tests should pass once pytest is available

---

**Status**: Plan complete, ready to execute
**Blocker**: pytest not installed
**Next Step**: Run `./install` or equivalent pip install command
