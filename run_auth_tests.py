#!/usr/bin/env python3
"""
Test runner for all authentication system tests.
"""
import os
import sys
import unittest
from io import StringIO

# Set up environment for testing
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
# Don't set REPL_ID to test local auth by default

def run_tests():
    """Run all authentication tests."""
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
    print(f"\n📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('\\n')[-2]}")
    
    # Return success/failure
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
