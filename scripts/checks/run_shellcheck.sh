#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
# shellcheck source=../../goto_root
source ../../goto_root
# Exclude reference/templates/servers/definitions/ as these are template files without shebangs
mapfile -t shell_scripts < <(git ls-files '*.sh' | grep -v '^reference/templates/servers/definitions/')
if [[ "${#shell_scripts[@]}" -eq 0 ]]; then
  echo "No shell scripts to lint."
  exit 0
fi
shellcheck --external-sources "${shell_scripts[@]}"
