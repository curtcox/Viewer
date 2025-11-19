#!/bin/bash
set -e

if [ -f pydoclint-report/summary.md ]; then
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat pydoclint-report/summary.md >>"${GITHUB_STEP_SUMMARY}"
  fi
fi
