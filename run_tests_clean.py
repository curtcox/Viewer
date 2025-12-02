#!/usr/bin/env python3
"""Run tests with a clean environment, bypassing autoenv completely."""

import os
import subprocess
import sys
from pathlib import Path

# Get the venv python path
venv_python = Path(__file__).parent / "venv" / "bin" / "python"
if not venv_python.exists():
    venv_python = Path(sys.executable)

# Build minimal clean environment
root_dir = Path(__file__).parent
env = {
    "PATH": str(venv_python.parent) + os.pathsep + os.environ.get("PATH", ""),
    "PYTHONPATH": str(root_dir),
    "DATABASE_URL": "sqlite:///:memory:",
    "SESSION_SECRET": "test-secret-key",
    "TESTING": "True",
    "GAUGE_ARTIFACT_DIR": str(root_dir / "reports" / "html-report" / "secureapp-artifacts"),
}

# Add PYTHONPATH for step_impl and tests
env["PYTHONPATH"] = os.pathsep.join([
    str(root_dir),
    str(root_dir / "step_impl"),
    str(root_dir / "tests"),
])

# Run pytest
cmd = [str(venv_python), "-m", "pytest", "tests/", "-m", "not integration", "-v"]
sys.exit(subprocess.call(cmd, cwd=str(root_dir), env=env))
