#!/bin/bash
set -e

mkdir -p shellcheck-report
STATUS=0
./scripts/checks/run_shellcheck.sh > shellcheck-report/output.txt 2>&1 || STATUS=$?
echo "exit_code=$STATUS" >> "$GITHUB_OUTPUT"

# Count files examined
FILE_COUNT=$(git ls-files '*.sh' | wc -l)
echo "Files examined: $FILE_COUNT" > shellcheck-report/summary.txt
echo "Exit code: $STATUS" >> shellcheck-report/summary.txt

if [ $STATUS -eq 0 ]; then
  echo "Status: ✓ All checks passed" >> shellcheck-report/summary.txt
else
  echo "Status: ✗ Issues found" >> shellcheck-report/summary.txt
fi

exit $STATUS
