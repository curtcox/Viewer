#!/bin/bash
# dirname server - Strip last path component
# Usage: /dirname/[ARGS][/input-source]
# - ARGS: optional arguments for the dirname command (use '_' to skip while piping)
# - input-source: optional chained input (server or CID providing stdin)

COMMAND="dirname"
COMMAND_PATH="$COMMAND"

if [[ -n "${BASH_COMMAND_STUB_DIR:-}" && -x "${BASH_COMMAND_STUB_DIR}/$COMMAND" ]]; then
    COMMAND_PATH="${BASH_COMMAND_STUB_DIR}/$COMMAND"
fi

arg_text="${1:-}"
if [[ "$arg_text" == "_" ]]; then
    arg_text=""
fi

args=()
if [[ -n "$arg_text" ]]; then
    # Split $1 into space-separated arguments
    read -r -a args <<< "$arg_text"
fi

if ! command -v "$COMMAND_PATH" >/dev/null 2>&1; then
    echo "Error: '$COMMAND' is not installed in this environment" >&2
    exit 127
fi

command "$COMMAND_PATH" "${args[@]}"
