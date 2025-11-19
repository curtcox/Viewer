#!/bin/bash
set -e

if [ -f vulture-report/summary.md ]; then
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat vulture-report/summary.md >>"${GITHUB_STEP_SUMMARY}"
  fi
fi
