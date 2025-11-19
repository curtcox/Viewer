#!/bin/bash
set -e

mkdir -p hadolint-report
STATUS=0
./scripts/checks/run_hadolint.sh > hadolint-report/output.txt 2>&1 || STATUS=$?
echo "exit_code=$STATUS" >> "$GITHUB_OUTPUT"

# Report the specific file examined
echo "File examined: docker/ci/Dockerfile" > hadolint-report/summary.txt
echo "Exit code: $STATUS" >> hadolint-report/summary.txt

if [ $STATUS -eq 0 ]; then
  echo "Status: ✓ All checks passed" >> hadolint-report/summary.txt
else
  echo "Status: ✗ Issues found" >> hadolint-report/summary.txt
fi

exit $STATUS
