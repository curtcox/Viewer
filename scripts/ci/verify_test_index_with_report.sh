#!/bin/bash
set -e

# Fix git ownership issue in container
git config --global --add safe.directory "$GITHUB_WORKSPACE"

mkdir -p test-index-report
STATUS=0
./scripts/checks/verify_test_index.sh > test-index-report/output.txt 2>&1 || STATUS=$?
echo "exit_code=$STATUS" >> "$GITHUB_OUTPUT"

# Copy TEST_INDEX.md to the report
if [ -f TEST_INDEX.md ]; then
  cp TEST_INDEX.md test-index-report/
fi

# Count tests in index
if [ -f TEST_INDEX.md ]; then
  TEST_COUNT=$(grep -c "^\- \[" TEST_INDEX.md || echo "0")
  echo "Tests indexed: $TEST_COUNT" > test-index-report/summary.txt
else
  echo "Tests indexed: 0" > test-index-report/summary.txt
fi
echo "Exit code: $STATUS" >> test-index-report/summary.txt

if [ $STATUS -eq 0 ]; then
  echo "Status: ✓ Index is valid" >> test-index-report/summary.txt
else
  echo "Status: ✗ Index validation failed" >> test-index-report/summary.txt
fi

exit $STATUS
