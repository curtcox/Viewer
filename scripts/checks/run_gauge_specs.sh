#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
source ../../goto_root
REPO_ROOT=$(pwd)
export GAUGE_PYTHON_COMMAND="${GAUGE_PYTHON_COMMAND:-python3}"
export STEP_IMPL_DIR="${STEP_IMPL_DIR:-${REPO_ROOT}/step_impl}"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${REPO_ROOT}:${REPO_ROOT}/step_impl:${REPO_ROOT}/tests"
export GAUGE_LOG_FILE="${GAUGE_LOG_FILE:-${REPO_ROOT}/reports/html-report/gauge-execution.log}"
./test-gauge "$@"
