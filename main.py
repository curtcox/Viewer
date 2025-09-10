import signal
import sys
from app import app
import routes  # noqa: F401

def signal_handler(sig, frame):
    print('\nShutting down gracefully...')
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print('\nShutting down gracefully...')
        sys.exit(0)
