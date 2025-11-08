#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
# shellcheck source=../../goto_root
source ../../goto_root
./test-unit -- --maxfail=1 -q "$@"
