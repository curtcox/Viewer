#!/usr/bin/env bash
set -euo pipefail

if ! git diff --exit-code TEST_INDEX.md; then
  echo "Error: TEST_INDEX.md is out of date!"
  echo "Please run 'python generate_test_index.py' and commit the changes."
  exit 1
fi

echo "Test index is up to date."
