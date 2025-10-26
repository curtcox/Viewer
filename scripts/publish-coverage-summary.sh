#!/usr/bin/env bash
set -euo pipefail

SUMMARY_FILE="${1:-test-unit/coverage.txt}"

if [[ ! -f "${SUMMARY_FILE}" && "${SUMMARY_FILE}" == "test-unit/coverage.txt" && -f "coverage-report.txt" ]]; then
  SUMMARY_FILE="coverage-report.txt"
fi

if [[ -f "${SUMMARY_FILE}" ]]; then
  cat "${SUMMARY_FILE}"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Coverage summary"
      echo '```'
      cat "${SUMMARY_FILE}"
      echo '```'
    } >> "${GITHUB_STEP_SUMMARY}"
  fi
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "generated=true" >> "${GITHUB_OUTPUT}"
  fi
else
  message="No coverage data found. Tests may not have run."
  echo "${message}"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "### Coverage summary"
      echo
      echo "No coverage data was generated."
    } >> "${GITHUB_STEP_SUMMARY}"
  fi
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "generated=false" >> "${GITHUB_OUTPUT}"
  fi
fi
