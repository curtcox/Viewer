#!/usr/bin/env python3
"""Run database equivalence tests."""

import os
import subprocess
import sys
from pathlib import Path

# Build minimal clean environment
root_dir = Path(__file__).parent
env = {
    "PATH": os.environ.get("PATH", ""),
    "PYTHONPATH": str(root_dir),
    "DATABASE_URL": "sqlite:///:memory:",
    "SESSION_SECRET": "test-secret-key",
    "TESTING": "True",
}

# Add PYTHONPATH for tests
env["PYTHONPATH"] = os.pathsep.join(
    [
        str(root_dir),
        str(root_dir / "tests"),
    ]
)


def main():
    """Run equivalence tests."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "db_equivalence",
        "-v",
        "--tb=short",
    ]

    # Add any additional arguments
    cmd.extend(sys.argv[1:])

    return subprocess.call(cmd, cwd=str(root_dir), env=env)


if __name__ == "__main__":
    sys.exit(main())
