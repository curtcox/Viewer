#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
source ../../goto_root
mapfile -t shell_scripts < <(git ls-files '*.sh')
if [[ "${#shell_scripts[@]}" -eq 0 ]]; then
  echo "No shell scripts to lint."
  exit 0
fi
shellcheck --external-sources "${shell_scripts[@]}"
