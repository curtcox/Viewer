import argparse
import signal
import sys
from typing import Any

from app import app


def signal_handler(_sig: Any, _frame: Any) -> None:
    print('\nShutting down gracefully...')
    sys.exit(0)


def handle_boot_cid_import(boot_cid: str) -> None:
    """Handle boot CID import if specified.

    Args:
        boot_cid: The CID to import on startup

    Raises:
        SystemExit: If the import fails
    """
    from boot_cid_importer import import_boot_cid  # pylint: disable=import-outside-toplevel
    from identity import ensure_default_user  # pylint: disable=import-outside-toplevel

    with app.app_context():
        # Get the default user
        default_user = ensure_default_user()

        # Perform the import
        success, error = import_boot_cid(app, boot_cid, default_user.id)

        if not success:
            print(f"\nBoot CID import failed:\n{error}", file=sys.stderr)
            sys.exit(1)

        print(f"Boot CID {boot_cid} imported successfully")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run the Viewer application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--boot-cid',
        type=str,
        help='Optional CID to import on startup. All referenced CIDs must exist in the database.',
    )
    args = parser.parse_args()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Handle boot CID import if specified
    if args.boot_cid:
        handle_boot_cid_import(args.boot_cid)

    try:
        app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print('\nShutting down gracefully...')
        sys.exit(0)
