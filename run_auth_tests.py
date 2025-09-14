#!/usr/bin/env python3
"""
Test runner for all authentication system tests.

These auth tests are segregated from the main test suite due to Flask-Login
initialization conflicts when running alongside other tests. They must be
run separately using this dedicated runner.
"""
import os
import sys
import unittest
from pathlib import Path

# Activate virtual environment if it exists
venv_path = Path(__file__).parent / 'venv'
if venv_path.exists():
    # Add venv to Python path - try multiple Python versions
    python_versions = ['python3.12', 'python3.11', 'python3.10', 'python3.9']
    for py_version in python_versions:
        venv_site_packages = venv_path / 'lib' / py_version / 'site-packages'
        if venv_site_packages.exists():
            sys.path.insert(0, str(venv_site_packages))
            break
    
    # Also add the venv bin directory for any executables
    venv_bin = venv_path / 'bin'
    if venv_bin.exists():
        os.environ['PATH'] = str(venv_bin) + ':' + os.environ.get('PATH', '')

# Set up environment for testing
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
# Don't set REPL_ID to test local auth by default

def run_tests():
    """Run all authentication tests."""
    print("🔐 Running segregated authentication test suite...\n")
    print("📝 These tests are separated from the main test suite due to Flask-Login conflicts.\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules
    test_modules = [
        'test_auth_providers',
        'test_local_auth',
        'test_auth_integration',
        'test_auth_templates'
    ]

    for module_name in test_modules:
        try:
            module = __import__(module_name)
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            print(f"✅ Loaded {module_name}: {tests.countTestCases()} tests")
        except ImportError as e:
            print(f"❌ Failed to import {module_name}: {e}")
        except Exception as e:
            print(f"❌ Error loading {module_name}: {e}")

    # Run tests
    print(f"\n🧪 Running {suite.countTestCases()} authentication tests...\n")

    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )

    result = runner.run(suite)

    # Print summary
    print("\n📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")

    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")

    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('\\n')[-2]}")

    # Return success/failure
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
