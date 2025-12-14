#!/bin/bash
# awk server - runs awk with the pattern from path parameter $1
# Usage: /awk/PATTERN/input-source
# - PATTERN: awk program (or CID containing awk program)
# - input-source: path to server/CID providing input data

awk "$1"
