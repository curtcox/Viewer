#!/usr/bin/env bash
set -eo pipefail

# shellcheck disable=SC2154
# INTEGRATION_LOG_PATH is provided by CI to control where the log is written.
LOG_PATH="${INTEGRATION_LOG_PATH:-integration-tests.log}"
LOG_DIR="$(dirname "$LOG_PATH")"
if [[ -n "$LOG_DIR" && "$LOG_DIR" != "." ]]; then
  mkdir -p "$LOG_DIR"
fi

python run_integration_tests.py "$@" | tee "$LOG_PATH"
