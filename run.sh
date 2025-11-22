#!/bin/bash
# run.sh - Convenience wrapper for running the Viewer application

# Default values
IN_MEMORY=""
PORT="5001"
DEBUG=""
BOOT_CID=""
SHOW=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --in-memory-db)
            IN_MEMORY="--in-memory-db"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            # HOST parameter is accepted but not used (main.py handles host binding)
            shift 2
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --boot-cid)
            BOOT_CID="--boot-cid $2"
            shift 2
            ;;
        --show)
            SHOW="--show"
            shift
            ;;
        --list)
            python main.py --list
            exit $?
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [URL] [CID]"
            echo ""
            echo "Options:"
            echo "  --in-memory-db    Run with an in-memory database"
            echo "  --port PORT       Port to run the server on (default: 5001)"
            echo "  --host HOST       Host to bind the server to (default: 0.0.0.0)"
            echo "  --debug           Run in debug mode"
            echo "  --boot-cid CID    Import a boot CID on startup"
            echo "  --show            Launch app and open in web browser"
            echo "  --list            List all valid boot CIDs"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            # Pass through positional arguments
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

# Run the application
# shellcheck disable=SC2086
python main.py $IN_MEMORY --port "$PORT" $DEBUG "$BOOT_CID" $SHOW "${POSITIONAL[@]}"
