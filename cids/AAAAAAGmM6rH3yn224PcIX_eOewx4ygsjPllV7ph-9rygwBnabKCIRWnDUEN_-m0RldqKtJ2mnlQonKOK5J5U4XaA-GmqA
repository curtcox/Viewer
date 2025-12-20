#!/bin/bash
# grep server - runs grep with the pattern from path parameter $1
# Usage: /grep/PATTERN/input-source
# - PATTERN: grep pattern (or CID containing grep pattern)
# - input-source: path to server/CID providing input data
# Returns matching lines; exit code 1 if no matches (returns 200 status)

# Use grep with -E for extended regex support
# Exit 0 even if no matches to avoid error status
grep -E "$1" || true
