#!/bin/bash
# md5sum server - Hash/check MD5 digests
# Usage: /md5sum/[ARGS][/input-source]
# - ARGS: optional arguments for the md5sum command (use '_' to skip while piping)
# - input-source: optional chained input (server or CID providing stdin)

COMMAND="md5sum"
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
