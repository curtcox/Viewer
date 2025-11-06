#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
cd "${REPO_ROOT}"
if ! command -v hadolint >/dev/null 2>&1; then
  echo "hadolint is not installed. Please install hadolint to run this check." >&2
  exit 1
fi
hadolint docker/ci/Dockerfile
