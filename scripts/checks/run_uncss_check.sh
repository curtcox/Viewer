#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
cd "${REPO_ROOT}"
if [[ ! -d node_modules ]]; then
  if [[ "${SKIP_NPM_INSTALL:-0}" == "1" ]]; then
    echo "node_modules directory missing and SKIP_NPM_INSTALL=1; skipping dependency installation." >&2
  else
    npm install
  fi
fi
npm run uncss:check "$@"
