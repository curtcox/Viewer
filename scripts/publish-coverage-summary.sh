#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC2154
# GITHUB_* environment variables are populated by GitHub Actions runners when available.
: "${GITHUB_STEP_SUMMARY:=}"
: "${GITHUB_OUTPUT:=}"

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 <report-path> [summary-path] [outputs-path]" >&2
  exit 1
fi

report_path="$1"
summary_target="${2:-${GITHUB_STEP_SUMMARY:-}}"
outputs_target="${3:-${GITHUB_OUTPUT:-}}"

gh_summary_available=false
if command -v gh >/dev/null 2>&1 && gh summary --help >/dev/null 2>&1; then
  gh_summary_available=true
fi

append_summary() {
  if [[ -n "${summary_target:-}" ]]; then
    cat >>"$summary_target"
  elif [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    cat >>"$GITHUB_STEP_SUMMARY"
  elif [[ "$gh_summary_available" == "true" ]]; then
    local tmp
    tmp=$(mktemp)
    cat >"$tmp"
    gh summary --append "$tmp" >/dev/null
    rm -f "$tmp"
  else
    cat
  fi
}

set_output() {
  local value="$1"
  if [[ -n "${outputs_target:-}" ]]; then
    printf '%s\n' "$value" >>"$outputs_target"
  elif [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf '%s\n' "$value" >>"$GITHUB_OUTPUT"
  else
    printf '%s\n' "$value"
  fi
}

if [[ -f "$report_path" ]]; then
  cat "$report_path"
  {
    echo "### Coverage summary"
    echo '```'
    cat "$report_path"
    echo '```'
  } | append_summary
  set_output "generated=true"
else
  message="No coverage data found. Tests may not have run."
  echo "$message" | tee "$report_path"
  {
    echo "### Coverage summary"
    echo
    echo "No coverage data was generated."
  } | append_summary
  set_output "generated=false"
fi
