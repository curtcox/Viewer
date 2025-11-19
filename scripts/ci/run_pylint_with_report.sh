#!/bin/bash
set -e

# Fix git ownership issue in container
git config --global --add safe.directory "$GITHUB_WORKSPACE"

mkdir -p pylint-report
STATUS=0
./scripts/checks/run_pylint.sh > pylint-report/output.txt 2>&1 || STATUS=$?
echo "exit_code=$STATUS" >> "$GITHUB_OUTPUT"

# Count files examined
FILE_COUNT=$(git ls-files '*.py' | wc -l)
echo "Files examined: $FILE_COUNT" > pylint-report/summary.txt
echo "Exit code: $STATUS" >> pylint-report/summary.txt

if [ $STATUS -eq 0 ]; then
  echo "Status: ✓ All checks passed" >> pylint-report/summary.txt
else
  echo "Status: ✗ Issues found" >> pylint-report/summary.txt
fi

exit $STATUS
