import argparse
import signal
import sys

from app import app


def signal_handler(_sig, _frame):
    print('\nShutting down gracefully...')
    sys.exit(0)


def get_default_boot_cid() -> str | None:
    """Get the default boot CID from reference_templates/boot.cid.

    Returns:
        The boot CID if the file exists and is readable, None otherwise
    """
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    boot_cid_file = Path(__file__).parent / "reference_templates" / "boot.cid"
    if boot_cid_file.exists():
        try:
            return boot_cid_file.read_text(encoding='utf-8').strip()
        except Exception:  # pylint: disable=broad-except
            return None
    return None


def handle_boot_cid_import(boot_cid: str) -> None:
    """Handle boot CID import if specified.

    Args:
        boot_cid: The CID to import on startup

    Raises:
        SystemExit: If the import fails
    """
    from boot_cid_importer import import_boot_cid  # pylint: disable=import-outside-toplevel

    try:
        with app.app_context():
            # Perform the import
            success, error = import_boot_cid(app, boot_cid)

            if not success:
                print(f"\nBoot CID import failed:\n{error}", file=sys.stderr)
                sys.exit(1)

            print(f"Boot CID {boot_cid} imported successfully")
    except Exception as e:  # pylint: disable=broad-except
        print("\nUnexpected error during boot CID import:", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def handle_list_boot_cids() -> None:
    """List all valid boot CIDs and exit."""
    from cli import list_boot_cids  # pylint: disable=import-outside-toplevel

    with app.app_context():
        boot_cids = list_boot_cids()

        if not boot_cids:
            print("No valid boot CIDs found in the database.")
            sys.exit(0)

        print(f"Found {len(boot_cids)} valid boot CID(s):\n")

        for cid_value, metadata in boot_cids:
            print(f"CID: {cid_value}")
            size = metadata.get('size')
            if size is not None:
                print(f"  Size: {size} bytes")
            uploaded_by = metadata.get('uploaded_by')
            if uploaded_by:
                print(f"  Uploaded by: {uploaded_by}")
            created_at = metadata.get('created_at')
            if created_at:
                print(f"  Created: {created_at}")
            sections = metadata.get('sections')
            if sections:
                print(f"  Sections: {', '.join(sections)}")
            print()

        sys.exit(0)


def handle_http_request(url: str) -> None:
    """Make an HTTP GET request and print the response.

    Args:
        url: URL or path to request

    Raises:
        SystemExit: Always exits after handling the request
    """
    from cli import make_http_get_request  # pylint: disable=import-outside-toplevel

    with app.app_context():
        success, response_text, status_code = make_http_get_request(app, url)

        if not success:
            print(f"Error: {response_text}", file=sys.stderr)
            sys.exit(1)

        # Print status code and response
        print(f"Status: {status_code}")
        print(response_text)

        # Exit with code based on HTTP status
        if status_code and status_code >= 400:
            sys.exit(1)
        sys.exit(0)


def parse_positional_arguments(positional_args: list[str]) -> tuple[str | None, str | None]:
    """Parse positional arguments and determine which are URLs and which are CIDs.

    Args:
        positional_args: List of positional arguments

    Returns:
        Tuple of (url, cid) where either or both may be None

    Raises:
        SystemExit: If arguments are invalid
    """
    from cli import is_valid_url, validate_cid  # pylint: disable=import-outside-toplevel

    if len(positional_args) == 0:
        return None, None

    if len(positional_args) > 2:
        print("Error: Too many positional arguments (maximum 2: URL and CID)", file=sys.stderr)
        sys.exit(1)

    url = None
    cid = None

    for arg in positional_args:
        # Check if it's clearly a URL (starts with /, http://, or https://)
        if arg.startswith('/') or arg.startswith('http://') or arg.startswith('https://'):
            is_valid, error = is_valid_url(arg)
            if not is_valid:
                print(f"Error: Invalid URL: {error}", file=sys.stderr)
                sys.exit(1)
            if url is not None:
                print("Error: Multiple URLs provided", file=sys.stderr)
                sys.exit(1)
            url = arg
        else:
            # Check if it looks like a URL with different scheme
            if '://' in arg:
                # Treat as URL and validate
                is_valid, error = is_valid_url(arg)
                if not is_valid:
                    print(f"Error: Invalid URL: {error}", file=sys.stderr)
                    sys.exit(1)
                if url is not None:
                    print("Error: Multiple URLs provided", file=sys.stderr)
                    sys.exit(1)
                url = arg
            else:
                # Try to validate as CID
                with app.app_context():
                    is_valid, error_type, error_msg = validate_cid(arg)

                    if not is_valid:
                        if error_type == 'invalid_format':
                            print(f"Error: Invalid CID: {error_msg}", file=sys.stderr)
                            sys.exit(1)
                        elif error_type == 'not_found':
                            print(f"Error: {error_msg}", file=sys.stderr)
                            sys.exit(1)
                        else:
                            print(f"Error: {error_msg}", file=sys.stderr)
                            sys.exit(1)

                if cid is not None:
                    print("Error: Multiple CIDs provided", file=sys.stderr)
                    sys.exit(1)
                cid = arg

    return url, cid


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run the Viewer application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # We'll handle --help ourselves
    )
    parser.add_argument(
        '--boot-cid',
        type=str,
        help='Optional CID to import on startup (legacy). Use positional CID argument instead.',
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all valid boot CIDs and exit',
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Launch the app and open it in the default web browser',
    )
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help='Show help message and exit',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Port to run the server on (default: 5001)',
    )
    parser.add_argument(
        'positional',
        nargs='*',
        help='URL and/or CID arguments',
    )
    args = parser.parse_args()

    # Handle --help
    if args.help:
        from cli import print_help  # pylint: disable=import-outside-toplevel
        print_help()
        sys.exit(0)

    # Handle --list
    if args.list:
        handle_list_boot_cids()

    # Parse positional arguments
    url, cid = parse_positional_arguments(args.positional)

    # Handle legacy --boot-cid flag
    if args.boot_cid:
        if cid is not None:
            print("Error: Cannot specify both --boot-cid and positional CID argument", file=sys.stderr)
            sys.exit(1)
        cid = args.boot_cid

    # Use default boot CID if no CID was specified and no URL (i.e., starting server)
    # Don't load default CID if just making an HTTP request
    if cid is None and url is None:
        default_cid = get_default_boot_cid()
        if default_cid:
            print(f"Using default boot CID from reference_templates/boot.cid: {default_cid}")
            cid = default_cid

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Handle boot CID import if specified
        if cid:
            handle_boot_cid_import(cid)

        # Handle HTTP GET request if URL specified (without --show)
        if url and not args.show:
            handle_http_request(url)

        # Handle --show flag (launch browser)
        if args.show:
            from cli import open_browser  # pylint: disable=import-outside-toplevel

            # Determine the URL to open
            if url:
                browser_url = url if url.startswith('http') else f"http://localhost:{args.port}{url}"
            else:
                browser_url = f"http://localhost:{args.port}"

            print(f"Opening browser to {browser_url}")
            # Open browser in a separate thread to not block the app startup
            import threading
            threading.Timer(1.0, lambda: open_browser(browser_url)).start()

        # Start the Flask app
        try:
            app.run(host="0.0.0.0", port=args.port, debug=True, use_reloader=False)
        except KeyboardInterrupt:
            print('\nShutting down gracefully...')
            sys.exit(0)
    except Exception as e:  # pylint: disable=broad-except
        print("\nFatal error starting application:", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
