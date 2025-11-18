#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
# shellcheck source=../../goto_root
source ../../goto_root
mapfile -t PY_FILES < <(git ls-files '*.py' '*.pyi')

if [ ${#PY_FILES[@]} -eq 0 ]; then
  echo "No Python files found to lint." >&2
  exit 0
fi

pylint --disable=C0114,C0115,C0116 "$@" "${PY_FILES[@]}"
