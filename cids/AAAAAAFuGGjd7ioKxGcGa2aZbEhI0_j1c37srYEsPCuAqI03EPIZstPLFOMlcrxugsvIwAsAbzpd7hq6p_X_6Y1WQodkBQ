#!/bin/bash
# jq server - runs jq with the filter from path parameter $1
# Usage: /jq/FILTER/input-source
# - FILTER: jq filter expression (or CID containing jq filter)
# - input-source: path to server/CID providing JSON input data

if [[ -z "$1" ]]; then
    echo "Error: jq filter required" >&2
    echo "Usage: /jq/FILTER/input-source" >&2
    exit 1
fi

jq "$1"
