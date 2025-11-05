#!/usr/bin/env python3
"""Run tests directly without triggering autoenv."""
import subprocess
import sys
from tests.test_support import build_test_environment, ROOT_DIR

if __name__ == "__main__":
    env = build_test_environment()
    cmd = [sys.executable, "-m", "pytest", "tests/", "-m", "not integration", "-v", "--tb=short"]
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    sys.exit(subprocess.call(cmd, cwd=str(ROOT_DIR), env=env))
