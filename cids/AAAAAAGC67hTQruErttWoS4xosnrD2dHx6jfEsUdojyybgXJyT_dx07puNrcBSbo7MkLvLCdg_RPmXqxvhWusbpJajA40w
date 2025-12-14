#!/bin/bash
# sed server - runs sed with the expression from path parameter $1
# Usage: /sed/EXPRESSION/input-source
# - EXPRESSION: sed expression (or CID containing sed expression)
# - input-source: path to server/CID providing input data

if [[ -z "$1" ]]; then
    echo "Error: sed expression required" >&2
    echo "Usage: /sed/EXPRESSION/input-source" >&2
    exit 1
fi

sed "$1"
