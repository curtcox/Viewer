#!/bin/bash
set -e

if [ -f python-smells-report/summary.md ]; then
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat python-smells-report/summary.md >>"${GITHUB_STEP_SUMMARY}"
  fi
fi
