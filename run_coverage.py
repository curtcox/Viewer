#!/usr/bin/env python3
"""
Coverage Analysis Script for Viewer Project

This script runs all tests with coverage analysis and generates reports.
Usage:
    python run_coverage.py [options]

Options:
    --html          Generate HTML coverage report
    --xml           Generate XML coverage report  
    --report        Show terminal coverage report (default)
    --all           Generate all report types
    --test PATTERN  Run specific test files matching pattern
    --fail-under N  Fail if coverage is under N percent
    --help          Show this help message
"""

import sys
import os
import subprocess
import argparse
import glob

def find_test_files(pattern=None):
    """Find all test files, optionally filtered by pattern."""
    if pattern:
        test_files = glob.glob(f"test_{pattern}*.py")
        if not test_files:
            test_files = glob.glob(f"*{pattern}*.py")
            test_files = [f for f in test_files if f.startswith('test_')]
    else:
        test_files = glob.glob("test_*.py")
    
    return sorted(test_files)

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}:")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Run tests with coverage analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--html', action='store_true', 
                       help='Generate HTML coverage report')
    parser.add_argument('--xml', action='store_true',
                       help='Generate XML coverage report')
    parser.add_argument('--report', action='store_true', default=True,
                       help='Show terminal coverage report (default)')
    parser.add_argument('--all', action='store_true',
                       help='Generate all report types')
    parser.add_argument('--test', metavar='PATTERN',
                       help='Run specific test files matching pattern')
    parser.add_argument('--fail-under', type=int, metavar='N',
                       help='Fail if coverage is under N percent')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # If --all is specified, enable all report types
    if args.all:
        args.html = True
        args.xml = True
        args.report = True
    
    # Find test files
    test_files = find_test_files(args.test)
    
    if not test_files:
        if args.test:
            print(f"No test files found matching pattern: {args.test}")
        else:
            print("No test files found!")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file}")
    
    # Clean up previous coverage data
    print("\nCleaning up previous coverage data...")
    for cleanup_file in ['.coverage', 'coverage.xml']:
        if os.path.exists(cleanup_file):
            os.remove(cleanup_file)
    
    if os.path.exists('htmlcov'):
        import shutil
        shutil.rmtree('htmlcov')
    
    # Run tests with coverage
    coverage_cmd = ['python3', '-m', 'coverage', 'run']
    
    if args.verbose:
        coverage_cmd.append('--debug=trace')
    
    # Add each test file
    coverage_cmd.extend(['-m', 'unittest'])
    
    # Convert test files to module names
    test_modules = []
    for test_file in test_files:
        if test_file.endswith('.py'):
            module_name = test_file[:-3]  # Remove .py extension
            test_modules.append(module_name)
    
    coverage_cmd.extend(test_modules)
    
    success = run_command(coverage_cmd, "Tests with coverage")
    
    if not success:
        print("\nTests failed! Coverage analysis may be incomplete.")
        # Continue anyway to show partial coverage
    
    # Generate reports
    reports_generated = []
    
    if args.report:
        cmd = ['python3', '-m', 'coverage', 'report']
        if args.fail_under:
            cmd.extend(['--fail-under', str(args.fail_under)])
        
        if run_command(cmd, "Coverage report"):
            reports_generated.append("Terminal report")
    
    if args.html:
        cmd = ['python3', '-m', 'coverage', 'html']
        if run_command(cmd, "HTML coverage report"):
            reports_generated.append("HTML report (htmlcov/index.html)")
    
    if args.xml:
        cmd = ['python3', '-m', 'coverage', 'xml']
        if run_command(cmd, "XML coverage report"):
            reports_generated.append("XML report (coverage.xml)")
    
    # Summary
    print(f"\n{'='*60}")
    print("COVERAGE ANALYSIS COMPLETE")
    print('='*60)
    
    if reports_generated:
        print("Reports generated:")
        for report in reports_generated:
            print(f"  ✓ {report}")
    
    if args.html and os.path.exists('htmlcov/index.html'):
        print(f"\nOpen HTML report: file://{os.path.abspath('htmlcov/index.html')}")
    
    print("\nUseful commands:")
    print("  python run_coverage.py --html     # Generate HTML report")
    print("  python run_coverage.py --all      # Generate all reports")
    print("  python run_coverage.py --test auth # Run only auth-related tests")
    print("  python run_coverage.py --fail-under 80 # Require 80% coverage")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
