#!/bin/bash
# sed server - runs sed with the expression from path parameter $1
# Usage: /sed/EXPRESSION/input-source
# - EXPRESSION: sed expression (or CID containing sed expression)
# - input-source: path to server/CID providing input data

sed "$1"
