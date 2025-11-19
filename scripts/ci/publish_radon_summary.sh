#!/bin/bash
set -e

if [ -f radon-report/summary.md ]; then
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat radon-report/summary.md >>"${GITHUB_STEP_SUMMARY}"
  fi
fi
