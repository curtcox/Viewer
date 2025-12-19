# cli_args.py
"""Command line argument parsing for the Viewer application."""

import argparse
import re

from db_config import DatabaseConfig, DatabaseMode
from readonly_config import ReadOnlyConfig


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

    return parser.parse_args()


def parse_memory_size(size_str: str) -> int:
    """Parse a memory size string like '1G', '512M', '100K' into bytes.

    Args:
        size_str: Memory size string (e.g., '1G', '512M', '100K')

    Returns:
        Size in bytes

    Raises:
        ValueError: If the size string is invalid
    """
    size_str = size_str.strip().upper()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$', size_str)

    if not match:
        raise ValueError(f"Invalid memory size format: {size_str}")

    value, unit = match.groups()
    value = float(value)

    multipliers = {
        '': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }

    return int(value * multipliers[unit])


def configure_from_args(args: argparse.Namespace) -> None:
    """Configure the application based on parsed arguments."""
    if args.in_memory_db:
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)

    # Handle read-only mode
    if hasattr(args, 'read_only') and args.read_only:
        ReadOnlyConfig.set_read_only_mode(True)
        # Read-only mode requires in-memory database
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)

        # Parse and set max CID memory
        if hasattr(args, 'max_cid_memory'):
            try:
                max_bytes = parse_memory_size(args.max_cid_memory)
                ReadOnlyConfig.set_max_cid_memory(max_bytes)
            except ValueError as e:
                raise ValueError(f"Invalid --max-cid-memory value: {e}") from e
