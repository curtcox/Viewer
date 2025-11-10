#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in the repository root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"
# shellcheck source=../goto_root
source ../goto_root

# Get the committed version from git and compare with the generated version
# The generated TEST_INDEX.md is already in the working directory (created by verify_test_index.sh)
ORIGINAL_INDEX=$(mktemp)

# Extract the committed version from git (if it exists)
if git rev-parse --git-dir > /dev/null 2>&1; then
  # We're in a git repository
  git show HEAD:TEST_INDEX.md > "$ORIGINAL_INDEX" 2>/dev/null || touch "$ORIGINAL_INDEX"
else
  # Not in a git repository, just touch an empty file
  touch "$ORIGINAL_INDEX"
fi

# Check if TEST_INDEX.md exists and is not empty
if [ ! -f "TEST_INDEX.md" ]; then
  echo ""
  echo "Error: TEST_INDEX.md is missing!"
  echo "Please run 'python generate_test_index.py' to generate it."
  rm -f "$ORIGINAL_INDEX"
  exit 1
fi

if [ ! -s "TEST_INDEX.md" ]; then
  echo ""
  echo "Error: TEST_INDEX.md is empty!"
  echo "Please run 'python generate_test_index.py' to generate it properly."
  rm -f "$ORIGINAL_INDEX"
  exit 1
fi

# Check if the original index file is empty (missing committed version)
if [ ! -s "$ORIGINAL_INDEX" ]; then
  echo ""
  echo "Error: No committed version of TEST_INDEX.md found in git!"
  echo "This may be the first time TEST_INDEX.md is being added."
  echo "Please run 'python generate_test_index.py' and commit TEST_INDEX.md."
  rm -f "$ORIGINAL_INDEX"
  exit 1
fi

# Compare the committed version with the newly generated version
if ! diff -u "$ORIGINAL_INDEX" TEST_INDEX.md; then
  echo ""
  echo "Error: TEST_INDEX.md is out of date!"
  echo "Please run 'python generate_test_index.py' and commit the changes."
  rm -f "$ORIGINAL_INDEX"
  exit 1
fi

rm -f "$ORIGINAL_INDEX"
echo "Test index is up to date."
