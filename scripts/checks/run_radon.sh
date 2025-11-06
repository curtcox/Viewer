#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
cd "${REPO_ROOT}"
OUTPUT_DIR="radon-report"
SUMMARY_FILE="${OUTPUT_DIR}/summary.md"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --summary-file)
      SUMMARY_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done
mkdir -p "$OUTPUT_DIR"
python scripts/run_radon.py --output-dir "$OUTPUT_DIR" --summary-file "$SUMMARY_FILE"
