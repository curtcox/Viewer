"""Response formatting and output encoding for server execution."""

import json
import traceback
from typing import Any

from flask import Response, redirect

from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid, get_extension_from_mime_type
from db_access import create_cid_record, get_cid_by_path
from server_execution.variable_resolution import _current_user_id


def _encode_output(output: Any) -> bytes:
    if isinstance(output, bytes):
        return output
    if isinstance(output, str):
        return output.encode("utf-8")
    # Dicts -> JSON for human-friendly output instead of concatenated keys
    if isinstance(output, dict):
        try:
            return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        except (TypeError, ValueError):
            # Fall back to string representation for non-JSON-serializable dicts
            return str(output).encode("utf-8")
    # If it's an iterable, try to handle common patterns gracefully
    try:
        from collections.abc import Iterable as _Iterable  # local import to avoid top changes
        if isinstance(output, _Iterable):
            items = list(output)
            # If elements look JSON-serializable (e.g., list of dicts), prefer JSON
            try:
                if items and any(isinstance(x, (dict, list, tuple)) for x in items):
                    return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            except Exception as json_err:  # pylint: disable=broad-exception-caught
                # Log all JSON encoding failures for debugging user code output
                print(f"[server_execution] JSON encoding attempt failed: {type(json_err).__name__}: {json_err}")
                print(f"[server_execution] Output type: {type(output).__name__}")
                print(f"[server_execution] Items types: {[type(x).__name__ for x in items[:5]]}...")
                traceback.print_exc()
                # Continue to try other encodings
            # List of ints -> bytes directly
            if all(isinstance(x, int) for x in items):
                return bytes(items)
            # List of bytes -> concatenate
            if all(isinstance(x, bytes) for x in items):
                return b"".join(items)
            # List of strings -> join then encode
            if all(isinstance(x, str) for x in items):
                return "".join(items).encode("utf-8")
    except (TypeError, ValueError, AttributeError):
        # Fall back to string representation for non-standard iterables
        pass

    # Fallback: encode the string representation
    return str(output).encode("utf-8")


def _log_server_output(debug_prefix: str, error_suffix: str, output: Any, content_type: str) -> None:
    """Log execution details while tolerating logging failures."""
    try:
        sample = repr(output)
        if sample and len(sample) > 300:
            sample = sample[:300] + "…"
        print(
            f"[server_execution] {debug_prefix}: output_type={type(output).__name__}, "
            f"content_type={content_type}, sample={sample}"
        )
    except (ValueError, TypeError, AttributeError) as debug_err:
        # Handle repr() failures or other logging errors gracefully
        suffix = f" {error_suffix}" if error_suffix else ""
        print(
            f"[server_execution] Debug output failed{suffix}: "
            f"{type(debug_err).__name__}: {debug_err}"
        )
        traceback.print_exc()


def _handle_successful_execution(output: Any, content_type: str, server_name: str) -> Response:
    output_bytes = _encode_output(output)
    cid_value = format_cid(generate_cid(output_bytes))

    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    user_id = _current_user_id()
    if not existing and cid_record_path and user_id:
        create_cid_record(cid_value, output_bytes, user_id)

    from server_execution.invocation_tracking import create_server_invocation_record
    if user_id:
        create_server_invocation_record(user_id, server_name, cid_value)

    extension = get_extension_from_mime_type(content_type)
    if extension and cid_record_path:
        redirect_path = cid_path(cid_value, extension)
        if redirect_path:
            return redirect(redirect_path)
    if cid_record_path:
        return redirect(cid_record_path)
    return redirect('/')
