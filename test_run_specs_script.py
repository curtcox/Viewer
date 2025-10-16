"""Tests for the lightweight spec runner."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_specs(*args: str) -> subprocess.CompletedProcess[str]:
    """Execute ``run_specs.py`` with the provided arguments."""

    repo_root = Path(__file__).resolve().parent
    script = repo_root / "run_specs.py"

    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def test_run_specs_script_executes_all_specs_successfully() -> None:
    """The helper script should execute every spec without failing."""

    result = _run_specs()

    assert result.returncode == 0, result.stderr or result.stdout
    assert "All specs passed." in result.stdout


def test_run_specs_script_fails_when_a_spec_is_invalid(tmp_path: Path) -> None:
    """A missing step should cause the runner to fail with a helpful error."""

    spec_path = tmp_path / "broken.spec"
    spec_path.write_text(
        "\n".join(
            [
                "# Broken suite",
                "",
                "## Scenario with missing implementation",
                "* This step does not exist",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_specs(str(spec_path))

    assert result.returncode != 0
    assert "Spec execution failed" in result.stdout
    assert "No step implementation found for: This step does not exist" in result.stdout
