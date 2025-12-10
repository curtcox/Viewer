#!/bin/bash
set -e

# Fix git ownership issue in container
if [ -n "${GITHUB_WORKSPACE:-}" ]; then
  git config --global --add safe.directory "$GITHUB_WORKSPACE"
fi

OUTPUT_DIR="cid-validation-report"
CID_DIR="/cids"

if [ ! -d "$CID_DIR" ] && [ -n "${GITHUB_WORKSPACE:-}" ] && [ -d "$GITHUB_WORKSPACE/cids" ]; then
  CID_DIR="$GITHUB_WORKSPACE/cids"
fi

mkdir -p "$OUTPUT_DIR"

STATUS=0
python scripts/checks/validate_cids.py --cid-dir "$CID_DIR" --output-dir "$OUTPUT_DIR" || STATUS=$?

echo "exit_code=$STATUS" >> "$GITHUB_OUTPUT"

exit $STATUS
