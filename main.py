import argparse
import logging
import os
import signal
import sys
from functools import lru_cache
from typing import Any, Mapping

from db_config import DatabaseConfig, DatabaseMode


@lru_cache(maxsize=4)
def _get_app_cached(config_items: tuple[tuple[str, Any], ...] | None):
    """Return a cached Flask application instance for the given config items."""
    from app import create_app  # pylint: disable=import-outside-toplevel

    config_override = dict(config_items) if config_items else None
    return create_app(config_override)


def _config_items(
    config_override: Mapping[str, Any] | None,
) -> tuple[tuple[str, Any], ...] | None:
    if not config_override:
        return None
    # Sort keys for deterministic cache keys
    return tuple(sorted(config_override.items()))


def get_app(config_override: Mapping[str, Any] | None = None):
    """Retrieve (and cache) a Flask app instance for the provided configuration."""

    return _get_app_cached(_config_items(config_override))


def configure_logging(debug_enabled: bool) -> int:
    """Configure root logging level and environment flag based on debug option."""

    log_level = logging.DEBUG if debug_enabled else logging.INFO
    os.environ["VIEWER_LOG_LEVEL"] = "DEBUG" if debug_enabled else "INFO"
    logging.basicConfig(level=log_level, force=True)
    logging.getLogger().setLevel(log_level)
    return log_level


# Expose a module-level application reference for code paths that monkeypatch main.app.
# It is intentionally not initialized eagerly so CLI-only flows can opt out by setting
# VIEWER_SKIP_MODULE_APP before requesting an application instance.
app = None


def signal_handler(_sig, _frame):
    print("\nShutting down gracefully...")
    sys.exit(0)


def get_default_boot_cid(readonly: bool = False) -> str | None:
    """Get the default boot CID from reference.templates.

    Args:
        readonly: If True, returns readonly.boot.cid instead of default

    Returns:
        The boot CID if the file exists and is readable, None otherwise
    """
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    filename = "readonly.boot.cid" if readonly else "boot.cid"
    boot_cid_file = Path(__file__).parent / "reference" / "templates" / filename
    if boot_cid_file.exists():
        try:
            return boot_cid_file.read_text(encoding="utf-8").strip()
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

    app_instance = globals().get("app") or get_app()

    try:
        with app_instance.app_context():
            # Perform the import
            success, error = import_boot_cid(app_instance, boot_cid)

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
    from sqlalchemy.exc import OperationalError
    import sqlite3
    import json
    from datetime import datetime

    def _list_boot_cids_from_sqlite(db_path: str) -> list[tuple[str, dict]]:
        conn = sqlite3.connect(db_path, timeout=1)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT path, file_data, file_size, created_at FROM cid")
            records = cursor.fetchall()
        except sqlite3.Error:
            return []
        finally:
            conn.close()

        boot_cids: list[tuple[str, dict]] = []
        for record in records:
            cid_value = (record["path"] or "").lstrip("/")
            if not cid_value:
                continue

            file_data = record["file_data"]
            if file_data is None:
                continue

            try:
                content = (
                    file_data.decode("utf-8")
                    if isinstance(file_data, (bytes, bytearray))
                    else str(file_data)
                )
                payload = json.loads(content)
            except Exception:
                continue

            if not isinstance(payload, dict):
                continue

            sections = [
                section
                for section in [
                    "aliases",
                    "servers",
                    "variables",
                    "secrets",
                    "change_history",
                ]
                if section in payload
            ]

            created_at = record["created_at"]
            try:
                created_at_value = (
                    datetime.fromisoformat(created_at)
                    if isinstance(created_at, str)
                    else created_at
                )
            except Exception:
                created_at_value = None

            metadata = {
                "size": record["file_size"],
                "created_at": created_at_value,
                "sections": sections,
            }

            boot_cids.append((cid_value, metadata))

        sentinel_date = datetime(1970, 1, 1)
        boot_cids.sort(
            key=lambda x: x[1]["created_at"]
            if x[1]["created_at"] is not None
            else sentinel_date,
            reverse=True,
        )
        return boot_cids

    def _render_boot_cids(boot_cids: list[tuple[str, dict]]) -> None:
        if not boot_cids:
            print("No valid boot CIDs found in the database.")
            sys.exit(0)

        print(f"Found {len(boot_cids)} valid boot CID(s):\n")

        for cid_value, metadata in boot_cids:
            print(f"CID: {cid_value}")
            size = metadata.get("size")
            if size is not None:
                print(f"  Size: {size} bytes")
            uploaded_by = metadata.get("uploaded_by")
            if uploaded_by:
                print(f"  Uploaded by: {uploaded_by}")
            created_at = metadata.get("created_at")
            if created_at:
                print(f"  Created: {created_at}")
            sections = metadata.get("sections")
            if sections:
                print(f"  Sections: {', '.join(sections)}")
            print()

        sys.exit(0)

    config_override = {"TESTING": True, "SKIP_DB_SETUP": True}

    # Use a lightweight app configuration to avoid unnecessary startup work for CLI-only invocation
    os.environ.setdefault("VIEWER_SKIP_MODULE_APP", "1")
    db_uri = DatabaseConfig.get_database_uri()
    if db_uri.startswith("sqlite:///"):
        sqlite_db_path = db_uri.replace("sqlite:///", "", 1)
        try:
            boot_cids = _list_boot_cids_from_sqlite(sqlite_db_path)
            _render_boot_cids(boot_cids)
        except sqlite3.Error:
            pass
    fast_cli_app = get_app(config_override)

    with fast_cli_app.app_context():
        try:
            boot_cids = list_boot_cids()
        except OperationalError:
            # Lazily create tables if they were skipped but are required for listing
            from database import db  # pylint: disable=import-outside-toplevel

            db.create_all()
            boot_cids = list_boot_cids()
        _render_boot_cids(boot_cids)


def handle_list_snapshots_command() -> None:
    """List available in-memory database snapshots and exit."""
    from db_snapshot import DatabaseSnapshot  # pylint: disable=import-outside-toplevel

    snapshots = DatabaseSnapshot.list_snapshots()
    if not snapshots:
        print("No database snapshots found.")
        sys.exit(0)

    print("Available database snapshots:\n")
    for name in snapshots:
        info = DatabaseSnapshot.get_snapshot_info(name) or {}
        created_at = info.get("created_at", "unknown time")
        print(f"- {name} (created {created_at})")
        table_counts = info.get("tables") or {}
        if table_counts:
            summary = ", ".join(
                f"{table}: {count}" for table, count in sorted(table_counts.items())
            )
            print(f"    tables: {summary}")
        print()

    sys.exit(0)


def handle_create_snapshot_command(name: str) -> None:
    """Create an in-memory database snapshot and exit."""
    if not DatabaseConfig.is_memory_mode():
        print(
            "Error: Snapshots require --in-memory-db to be enabled.",
            file=sys.stderr,
        )
        sys.exit(1)

    from db_snapshot import DatabaseSnapshot  # pylint: disable=import-outside-toplevel

    app = get_app()

    with app.app_context():
        snapshot_path = DatabaseSnapshot.create_snapshot(name)

    print(f"Snapshot stored at {snapshot_path}")
    sys.exit(0)


def handle_http_request(url: str) -> None:
    """Make an HTTP GET request and print the response.

    Args:
        url: URL or path to request

    Raises:
        SystemExit: Always exits after handling the request
    """
    from cli import make_http_get_request  # pylint: disable=import-outside-toplevel

    app = get_app()

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


def parse_positional_arguments(
    positional_args: list[str],
) -> tuple[str | None, str | None]:
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
        print(
            "Error: Too many positional arguments (maximum 2: URL and CID)",
            file=sys.stderr,
        )
        sys.exit(1)

    url = None
    cid = None

    app = get_app()

    for arg in positional_args:
        # Check if it's clearly a URL (starts with /, http://, or https://)
        if (
            arg.startswith("/")
            or arg.startswith("http://")
            or arg.startswith("https://")
        ):
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
            if "://" in arg:
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
                        if error_type == "invalid_format":
                            print(f"Error: Invalid CID: {error_msg}", file=sys.stderr)
                            sys.exit(1)
                        elif error_type == "not_found":
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


def should_use_default_boot_cid(
    *, cid: str | None, url: str | None
) -> bool:
    if cid is not None:
        return False
    return url is None


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run the Viewer application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # We'll handle --help ourselves
    )
    parser.add_argument(
        "--boot-cid",
        type=str,
        help="Optional CID to import on startup (legacy). Use positional CID argument instead.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all valid boot CIDs and exit",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Launch the app and open it in the default web browser",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Show help message and exit",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port to run the server on (default: 5001)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode",
    )
    parser.add_argument(
        "--in-memory-db",
        action="store_true",
        help="Run the application with an in-memory database",
    )
    parser.add_argument(
        "--dump-db-on-exit",
        type=str,
        help="Dump the in-memory database to the specified file on exit",
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        metavar="NAME",
        help="Create an in-memory database snapshot with the provided name",
    )
    parser.add_argument(
        "--list-snapshots",
        action="store_true",
        help="List available in-memory database snapshots and exit",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run in read-only mode with in-memory database",
    )
    parser.add_argument(
        "--max-cid-memory",
        type=str,
        default="1G",
        help="Maximum memory for CID storage in read-only mode (default: 1G, e.g., 100M, 2G)",
    )
    parser.add_argument(
        "positional",
        nargs="*",
        help="URL and/or CID arguments",
    )
    args = parser.parse_args()

    # Configure logging early so subsequent imports respect the chosen level.
    configure_logging(args.debug)

    # Configure database mode (must be done before app is accessed)
    if args.read_only:
        from readonly_config import ReadOnlyConfig  # pylint: disable=import-outside-toplevel
        from cli_args import parse_memory_size  # pylint: disable=import-outside-toplevel

        ReadOnlyConfig.set_read_only_mode(True)
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)

        # Parse and set max CID memory
        try:
            max_bytes = parse_memory_size(args.max_cid_memory)
            ReadOnlyConfig.set_max_cid_memory(max_bytes)
        except ValueError as e:
            print(f"Error: Invalid --max-cid-memory value: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.in_memory_db:
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)

    # Handle --help
    if args.help:
        from cli import print_help  # pylint: disable=import-outside-toplevel

        print_help()
        sys.exit(0)

    if args.list_snapshots:
        handle_list_snapshots_command()

    if args.snapshot:
        handle_create_snapshot_command(args.snapshot)

    # Handle --list
    if args.list:
        handle_list_boot_cids()

    # Parse positional arguments
    url, cid = parse_positional_arguments(args.positional)

    # Handle legacy --boot-cid flag
    if args.boot_cid:
        if cid is not None:
            print(
                "Error: Cannot specify both --boot-cid and positional CID argument",
                file=sys.stderr,
            )
            sys.exit(1)
        cid = args.boot_cid

    # Use default boot CID if no CID was specified.
    # For internal URLs (paths starting with /), we still want the boot image loaded
    # so that variables like "gateways" are available.
    if should_use_default_boot_cid(cid=cid, url=url):
        default_cid = get_default_boot_cid(readonly=args.read_only)
        if default_cid:
            boot_type = "readonly" if args.read_only else "default"
            print(f"Using {boot_type} boot CID from reference/templates: {default_cid}")
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
                browser_url = (
                    url
                    if url.startswith("http")
                    else f"http://localhost:{args.port}{url}"
                )
            else:
                browser_url = f"http://localhost:{args.port}"

            print(f"Opening browser to {browser_url}")
            # Open browser in a separate thread to not block the app startup
            import threading

            threading.Timer(1.0, lambda: open_browser(browser_url)).start()

        # Start the Flask app
        app = get_app()
        try:
            app.run(
                host="0.0.0.0",
                port=args.port,
                debug=args.debug,
                use_reloader=False,
            )
        except KeyboardInterrupt:
            print("\nShutting down gracefully...")
        finally:
            if args.dump_db_on_exit and args.in_memory_db:
                try:
                    from db_snapshot import DatabaseSnapshot

                    print(f"Dumping in-memory database to {args.dump_db_on_exit}...")
                    with app.app_context():
                        DatabaseSnapshot.dump_to_sqlite(args.dump_db_on_exit)
                    print("Database dump completed.")
                except Exception as e:
                    print(f"Failed to dump database: {e}", file=sys.stderr)

            if not args.dump_db_on_exit and args.in_memory_db:
                print(
                    "Note: In-memory database lost on exit. Use --dump-db-on-exit to save."
                )

    except Exception as e:  # pylint: disable=broad-except
        print("\nFatal error starting application:", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
