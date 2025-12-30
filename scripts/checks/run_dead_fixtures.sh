#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
# shellcheck source=../../goto_root
source ../../goto_root
# Run dead-fixtures check across all tests (including integration tests)
# Clear addopts from pytest.ini to include integration tests
PYTHON_BIN=

if [[ -n "${VIRTUAL_ENV:-}" ]] && [[ -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
else
  echo "Error: could not find a Python interpreter (tried venv, python, python3)" >&2
  exit 1
fi

"${PYTHON_BIN}" -m pytest --override-ini addopts= --dead-fixtures -q "$@"
