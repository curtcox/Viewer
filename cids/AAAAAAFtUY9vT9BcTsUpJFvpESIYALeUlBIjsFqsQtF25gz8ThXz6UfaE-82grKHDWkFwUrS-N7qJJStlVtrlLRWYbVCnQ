#!/bin/bash
# awk server - runs awk with the pattern from path parameter $1
# Usage: /awk/PATTERN/input-source
# - PATTERN: awk program (or CID containing awk program)
# - input-source: path to server/CID providing input data

if [[ -z "$1" ]]; then
    echo "Error: awk pattern required" >&2
    echo "Usage: /awk/PATTERN/input-source" >&2
    exit 1
fi

awk "$1"
