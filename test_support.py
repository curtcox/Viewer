"""Helper utilities shared by test runner scripts."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

DEFAULT_ENV = {
    "DATABASE_URL": "sqlite:///:memory:",
    "SESSION_SECRET": "test-secret-key",
    "TESTING": "True",
}


def build_test_environment() -> dict[str, str]:
    """Return a copy of the environment with repository defaults applied."""

    env = os.environ.copy()
    python_path = env.get("PYTHONPATH")
    search_paths = [str(ROOT_DIR), str(ROOT_DIR / "step_impl"), str(ROOT_DIR / "tests")]
    if python_path:
        search_paths.append(python_path)
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(search_paths))

    for key, value in DEFAULT_ENV.items():
        env.setdefault(key, value)

    return env


def locate_gauge() -> str:
    """Return the path to the Gauge CLI or raise ``FileNotFoundError``."""

    gauge_cmd = shutil.which("gauge")
    if gauge_cmd is None:
        msg = (
            "Gauge CLI not found. Install Gauge from "
            "https://docs.gauge.org/getting_started/installing-gauge.html"
        )
        raise FileNotFoundError(msg)
    return gauge_cmd
