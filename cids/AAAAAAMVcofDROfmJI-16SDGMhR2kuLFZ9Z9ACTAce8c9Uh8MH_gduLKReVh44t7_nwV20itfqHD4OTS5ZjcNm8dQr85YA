#!/bin/bash
# grep server - runs grep with the pattern from path parameter $1
# Usage: /grep/PATTERN/input-source
# - PATTERN: grep pattern (or CID containing grep pattern)
# - input-source: path to server/CID providing input data
# Returns matching lines; exit code 0 for matches, 1 for no matches

if [[ -z "$1" ]]; then
    echo "Error: grep pattern required" >&2
    echo "Usage: /grep/PATTERN/input-source" >&2
    exit 1
fi

# Use grep with -E for extended regex support
grep -E "$1"
exit_code=$?

if [[ $exit_code -eq 0 ]]; then
    # Matches found
    exit 0
elif [[ $exit_code -eq 1 ]]; then
    # No matches - not an error, just no output
    exit 0
else
    # Real error (exit code 2 or higher)
    echo "Error: grep failed with exit code $exit_code" >&2
    exit $exit_code
fi
