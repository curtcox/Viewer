"""CID path resolution and metadata for meta route."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import url_for

from cid_presenter import cid_path, format_cid
from db_access import find_server_invocations_by_cid, get_cid_by_path, get_servers
from entity_references import extract_references_from_bytes
from server_execution.language_detection import detect_server_language

from .meta_path_utils import dedupe_links, split_extension

META_SOURCE_LINK = "/source/routes/meta.py"


def server_events_for_cid(cid_value: str) -> List[Dict[str, Any]]:
    """Return server invocation metadata for the supplied CID."""
    if not cid_value:
        return []

    invocations = find_server_invocations_by_cid(cid_value)
    if not invocations:
        return []

    events: List[Dict[str, Any]] = []
    cid_fields = {
        "result_cid": "result",
        "invocation_cid": "invocation",
        "request_details_cid": "request_details",
        "servers_cid": "servers",
        "variables_cid": "variables",
        "secrets_cid": "secrets",
    }

    for invocation in invocations:
        related_meta_links: List[str] = []
        related_cids: Dict[str, str] = {}
        for field, label in cid_fields.items():
            value = getattr(invocation, field, None)
            if not value:
                continue
            formatted_value = format_cid(value)
            if not formatted_value:
                continue
            related_cids[label] = formatted_value
            related_meta_links.append(
                url_for("main.meta_route", requested_path=formatted_value)
            )

        events.append(
            {
                "server_name": invocation.server_name,
                "event_page": url_for("main.server_events"),
                "invoked_at": invocation.invoked_at.isoformat() if invocation.invoked_at else None,
                "related_cids": related_cids,
                "related_cid_meta_links": dedupe_links(related_meta_links),
            }
        )

    return events


def resolve_cid_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for CID-backed content."""
    base_path, extension = split_extension(path)
    if not base_path.startswith("/"):
        return None

    cid_value = format_cid(base_path)
    cid_record_path = cid_path(cid_value)
    if not cid_record_path:
        return None

    cid_record = get_cid_by_path(cid_record_path)
    if not cid_record:
        return None

    record: Dict[str, Any] = {
        "cid": cid_value,
        "path": cid_record_path,
        "file_size": cid_record.file_size,
        "created_at": cid_record.created_at.isoformat() if cid_record.created_at else None,
    }

    metadata: Dict[str, Any] = {
        "path": path,
        "status_code": 200,
        "resolution": {
            "type": "cid",
            "cid": cid_value,
            "extension": extension,
            "record": record,
        },
        "source_links": dedupe_links([
            "/source/routes/core.py",
            "/source/cid_utils.py",
            META_SOURCE_LINK,
        ]),
    }

    # Check if this CID is associated with any named server definitions
    servers = get_servers()
    server_info = None
    for server in servers:
        if server.definition_cid == cid_value:
            # Use detected language from server definition
            language = detect_server_language(server.definition)
            server_info = {
                "name": server.name,
                "enabled": server.enabled,
                "supports_chaining": True,  # Servers can accept chained input
                "language": language,
            }
            break

    # If not a named server, check if the CID content is a server definition
    if not server_info and cid_record and cid_record.file_data:
        try:
            content = cid_record.file_data.decode('utf-8', errors='ignore')
            language = detect_server_language(content)

            # Heuristic: if language is detected as bash or python (not default),
            # and content looks like executable code, treat it as a server
            if language in ('bash', 'python', 'typescript', 'clojure', 'clojurescript'):
                # Check if content appears to be executable (has def main, shebang, or common patterns)
                is_server = (
                    'def main(' in content or
                    content.strip().startswith('#!') or
                    'echo ' in content or
                    'grep ' in content or
                    'function main' in content
                )

                if is_server:
                    server_info = {
                        "name": None,  # Anonymous server
                        "enabled": True,
                        "supports_chaining": True,  # Server literals can accept chained input
                        "language": language,
                    }
        except Exception:
            # If we can't decode or analyze, skip server detection
            pass

    if server_info:
        metadata["resolution"]["server"] = server_info

    server_events = server_events_for_cid(cid_value)
    if server_events:
        metadata["server_events"] = server_events
        metadata["source_links"] = dedupe_links(metadata["source_links"] + ["/source/server_execution.py"])

    references = extract_references_from_bytes(
        getattr(cid_record, "file_data", None),
    )
    if any(references.values()):
        metadata["referenced_entities"] = references

    return metadata
