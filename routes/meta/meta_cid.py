"""CID path resolution and metadata for meta route."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import url_for

from cid_presenter import cid_path, format_cid
from db_access import find_server_invocations_by_cid, get_cid_by_path
from entity_references import extract_references_from_bytes

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
        "uploaded_by_user_id": cid_record.uploaded_by_user_id,
    }

    if cid_record.uploaded_by_user_id:
        record["uploaded_by"] = {
            "user_id": cid_record.uploaded_by_user_id,
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
