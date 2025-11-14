"""Command-line interface utilities for the Viewer application."""

import json
import sys
import webbrowser
from typing import Optional, Tuple
from urllib.parse import urlparse

from flask import Flask

from cid_core import is_normalized_cid, normalize_component, is_probable_cid_component
from cid_presenter import cid_path
from db_access import get_cid_by_path
from models import CID


def is_valid_url(value: str) -> Tuple[bool, Optional[str]]:
    """Check if a string is a valid URL.

    Args:
        value: String to check

    Returns:
        Tuple of (is_valid, error_message)
        If valid, returns (True, None)
        If invalid, returns (False, error_message)
    """
    # Check if it starts with '/'
    if value.startswith('/'):
        return True, None

    # Parse the URL
    try:
        parsed = urlparse(value)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    # Check for valid scheme
    if not parsed.scheme:
        return False, "URL must have a scheme (e.g., http:// or https://)"

    if parsed.scheme not in ('http', 'https'):
        return False, f"URL scheme must be http or https, got: {parsed.scheme}"

    # Check for netloc (domain/host)
    if not parsed.netloc:
        return False, "URL must have a host/domain"

    return True, None


def validate_cid(cid_value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate a CID string.

    Args:
        cid_value: String to validate as a CID

    Returns:
        Tuple of (is_valid, error_type, error_message)
        - If valid CID that exists: (True, None, None)
        - If valid CID not found: (False, 'not_found', message)
        - If invalid CID format: (False, 'invalid_format', message)
    """
    # Check for invalid characters before normalization
    if not cid_value or not cid_value.strip():
        return False, 'invalid_format', "CID cannot be empty"

    if '.' in cid_value:
        return False, 'invalid_format', f"CID contains invalid character '.': {cid_value}"

    # Check for slashes (except leading ones which are stripped during normalization)
    stripped = cid_value.lstrip('/')
    if '/' in stripped:
        return False, 'invalid_format', f"CID contains invalid character '/': {cid_value}"

    normalized = normalize_component(cid_value)

    # Check if it looks like a CID at all
    if not is_probable_cid_component(normalized):
        # Try to explain why it's not valid
        if not normalized:
            return False, 'invalid_format', "CID cannot be empty"

        # Check for other invalid characters
        invalid_chars = set(normalized) - set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-')
        if invalid_chars:
            return False, 'invalid_format', f"CID contains invalid characters: {', '.join(sorted(invalid_chars))}"

        if len(normalized) < 6:
            return False, 'invalid_format', f"CID is too short (minimum 6 characters): {cid_value}"

        return False, 'invalid_format', f"Not a valid CID format: {cid_value}"

    # Check if it's a properly formatted CID
    if not is_normalized_cid(normalized):
        return False, 'invalid_format', f"CID is not in normalized format: {cid_value}"

    # Check if CID exists in database
    path = cid_path(normalized)
    if not path:
        return False, 'invalid_format', f"Could not determine path for CID: {cid_value}"

    cid_record = get_cid_by_path(path)
    if not cid_record:
        return False, 'not_found', f"CID not found in database: {cid_value}\nMake sure the CID file exists in the cids directory or has been uploaded."

    return True, None, None


def is_valid_boot_cid(cid_record: CID) -> Tuple[bool, Optional[str]]:
    """Check if a CID is a valid boot CID (must be a JSON object).

    Args:
        cid_record: CID database record

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not cid_record.file_data:
        return False, "CID has no content"

    try:
        content = cid_record.file_data.decode('utf-8')
    except UnicodeDecodeError:
        return False, "Content is not valid UTF-8"

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return False, "Content is not valid JSON"

    if not isinstance(payload, dict):
        return False, f"Content must be a JSON object, got {type(payload).__name__}"

    return True, None


def list_boot_cids() -> list[Tuple[str, dict]]:
    """List all CIDs that are valid boot CIDs.

    Returns:
        List of tuples: (cid_value, metadata)
        where metadata includes: size, uploaded_by, created_at, has_sections
    """
    all_cids = CID.query.all()
    boot_cids = []

    for cid_record in all_cids:
        # Extract CID value from path (remove leading '/')
        cid_value = cid_record.path.lstrip('/') if cid_record.path else None
        if not cid_value:
            continue

        # Check if it's a valid boot CID
        is_valid, _ = is_valid_boot_cid(cid_record)
        if not is_valid:
            continue

        # Parse the JSON to get section info
        try:
            content = cid_record.file_data.decode('utf-8')
            payload = json.loads(content)
            sections = []
            for section in ['aliases', 'servers', 'variables', 'secrets', 'change_history']:
                if section in payload:
                    sections.append(section)
        except Exception:
            sections = []

        metadata = {
            'size': cid_record.file_size,
            'uploaded_by': cid_record.uploaded_by_user_id,
            'created_at': cid_record.created_at,
            'sections': sections,
        }

        boot_cids.append((cid_value, metadata))

    # Sort by creation date (newest first), handling None values
    # None values should come last, so use a very old date for them
    # (since we're sorting in reverse, old dates will be sorted to the end)
    from datetime import datetime
    # Use a sentinel value that's timezone-naive to avoid comparison issues
    sentinel_date = datetime(1970, 1, 1)
    boot_cids.sort(
        key=lambda x: x[1]['created_at'] if x[1]['created_at'] is not None
                     else sentinel_date,
        reverse=True
    )

    return boot_cids


def make_http_get_request(app: Flask, url: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """Make an HTTP GET request to the app and return the response.

    Args:
        app: Flask application instance
        url: URL or path to request (e.g., '/path' or 'http://localhost:5001/path')

    Returns:
        Tuple of (success, response_text, status_code)
        If successful, returns (True, response_text, status_code)
        If error, returns (False, error_message, None)
    """
    # Extract path from URL if it's a full URL
    if url.startswith('http://') or url.startswith('https://'):
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path += '?' + parsed.query
    else:
        path = url

    # Ensure path starts with '/'
    if not path.startswith('/'):
        path = '/' + path

    # Create a test client and make the request
    try:
        with app.test_client() as client:
            response = client.get(path)

            # Get response data as text
            if response.data:
                try:
                    response_text = response.data.decode('utf-8')
                except UnicodeDecodeError:
                    # If it's binary data, show a message
                    response_text = f"[Binary data: {len(response.data)} bytes]"
            else:
                response_text = ""

            return True, response_text, response.status_code
    except Exception as e:
        return False, f"Error making HTTP request: {e}", None


def open_browser(url: str) -> bool:
    """Open the default web browser to the specified URL.

    Args:
        url: URL to open

    Returns:
        True if successful, False otherwise
    """
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"Warning: Could not open browser: {e}", file=sys.stderr)
        return False


def print_help():
    """Print detailed help for CLI options."""
    help_text = """
Viewer Application - Command Line Interface

USAGE:
    python main.py [OPTIONS] [URL] [CID]

OPTIONS:
    --help              Show this help message and exit
    --list              List all valid boot CIDs and exit
    --show              Launch the app and open it in the default web browser
    --boot-cid CID      Import a boot CID on startup (legacy, use positional CID instead)
    --port PORT         Port to run the server on (default: 5001)

ARGUMENTS:
    URL                 A URL to make a GET request to (must start with http://, https://, or /)
                        When provided alone, returns the response and exits

    CID                 A Content Identifier to use as a boot CID
                        When provided alone, imports the CID and starts the app

    URL and CID         When both provided, makes GET request and imports boot CID

EXAMPLES:
    # Launch the app normally
    python main.py

    # Make a GET request and print the response
    python main.py /dashboard
    python main.py http://localhost:5001/servers

    # Import a boot CID and start the app
    python main.py AAAABP7x8...

    # Import boot CID and make GET request
    python main.py http://localhost:5001/status AAAABP7x8...

    # List all valid boot CIDs
    python main.py --list

    # Launch app and open browser
    python main.py --show
    python main.py --show http://localhost:5001/dashboard

NOTES:
    - Boot CIDs must be valid JSON objects stored in the database
    - CID files should be placed in the cids/ directory before starting
    - URLs can be absolute (http://...) or relative (/)
    - Use Ctrl+C to stop the application
"""
    print(help_text)


__all__ = [
    'is_valid_url',
    'validate_cid',
    'is_valid_boot_cid',
    'list_boot_cids',
    'make_http_get_request',
    'open_browser',
    'print_help',
]
