#!/usr/bin/env bash
set -eo pipefail

LOG_PATH="${INTEGRATION_LOG_PATH:-integration-tests.log}"
LOG_DIR="$(dirname "$LOG_PATH")"
if [[ -n "$LOG_DIR" && "$LOG_DIR" != "." ]]; then
  mkdir -p "$LOG_DIR"
fi

python run_integration_tests.py "$@" | tee "$LOG_PATH"
