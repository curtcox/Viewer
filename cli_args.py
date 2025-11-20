# cli_args.py
"""Command line argument parsing for the Viewer application."""

import argparse

from db_config import DatabaseConfig, DatabaseMode


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the application."""
    parser = argparse.ArgumentParser(description="Viewer Application")

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
        "--port",
        type=int,
        default=5000,
        help="Port to run the server on (default: 5000)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode",
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

    return parser.parse_args()


def configure_from_args(args: argparse.Namespace) -> None:
    """Configure the application based on parsed arguments."""
    if args.in_memory_db:
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
