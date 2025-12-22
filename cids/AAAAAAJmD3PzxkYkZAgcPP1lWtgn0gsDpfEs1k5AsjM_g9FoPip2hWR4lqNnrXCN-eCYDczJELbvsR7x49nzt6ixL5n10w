#!/bin/bash
# stat server - Detailed file metadata
# Usage: /stat/[ARGS][/input-source]
# - ARGS: optional arguments for the stat command (use '_' to skip while piping)
# - input-source: optional chained input (server or CID providing stdin)

COMMAND="stat"
arg_text="${1:-}"
if [[ "$arg_text" == "_" ]]; then
    arg_text=""
fi

args=()
if [[ -n "$arg_text" ]]; then
    # Split $1 into space-separated arguments
    read -r -a args <<< "$arg_text"
fi

if ! command -v "$COMMAND" >/dev/null 2>&1; then
    echo "Error: '$COMMAND' is not installed in this environment" >&2
    exit 127
fi

"$COMMAND" "${args[@]}"
