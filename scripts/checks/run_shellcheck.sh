#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
cd "${REPO_ROOT}"
mapfile -t shell_scripts < <(git ls-files '*.sh')
if [[ "${#shell_scripts[@]}" -eq 0 ]]; then
  echo "No shell scripts to lint."
  exit 0
fi
shellcheck "${shell_scripts[@]}"
