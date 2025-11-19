#!/bin/bash
set -e

mkdir -p dead-fixtures-report
STATUS=0
./scripts/checks/run_dead_fixtures.sh > dead-fixtures-report/output.txt 2>&1 || STATUS=$?
echo "exit_code=$STATUS" >> "$GITHUB_OUTPUT"

# Create summary
echo "Dead Fixtures Check" > dead-fixtures-report/summary.txt
echo "Exit code: $STATUS" >> dead-fixtures-report/summary.txt

if [ $STATUS -eq 0 ]; then
  echo "Status: ✓ No dead fixtures found" >> dead-fixtures-report/summary.txt
else
  echo "Status: ✗ Dead fixtures detected" >> dead-fixtures-report/summary.txt
fi

exit $STATUS
