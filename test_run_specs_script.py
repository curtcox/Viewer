"""Tests for the lightweight spec runner."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_specs_script_executes_all_specs_successfully() -> None:
    """The helper script should execute every spec without failing."""

    repo_root = Path(__file__).resolve().parent
    script = repo_root / "run_specs.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "All specs passed." in result.stdout
