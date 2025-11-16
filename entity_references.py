"""Utilities for extracting cross-entity references from text content."""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlsplit

from flask import url_for

from cid_presenter import cid_path, format_cid
from cid_utils import CID_PATH_CAPTURE_PATTERN, is_probable_cid_component
from db_access import (
    get_alias_by_name,
    get_aliases,
    get_cid_by_path,
    get_cids_by_paths,
    get_server_by_name,
    get_servers,
)

ReferenceMap = Dict[str, List[Dict[str, str]]]

_NAME_BOUNDARY = r"(?![A-Za-z0-9._-])"
_MAX_SCAN_LENGTH = 100_000


def _empty_reference_map() -> ReferenceMap:
    return {"aliases": [], "servers": [], "cids": []}


def _normalize_local_path(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    parsed = urlsplit(stripped)
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path or ""
    if not path:
        return None

    if not path.startswith("/"):
        path = f"/{path}"

    return path


def _strip_extension(path: str) -> str:
    last_segment = path.rsplit("/", 1)[-1]
    if "." not in last_segment:
        return path

    base_segment = last_segment.split(".", 1)[0]
    if "/" not in path:
        return base_segment

    prefix = path.rsplit("/", 1)[0]
    if not prefix:
        return f"/{base_segment}"
    return f"{prefix}/{base_segment}"


def _build_alias_reference(name: str) -> Dict[str, str]:
    return {
        "name": name,
        "url": url_for("main.view_alias", alias_name=name),
    }


def _build_server_reference(name: str) -> Dict[str, str]:
    return {
        "name": name,
        "url": url_for("main.view_server", server_name=name),
    }


def _build_cid_reference(value: str) -> Dict[str, str]:
    normalized = format_cid(value)
    return {
        "cid": normalized,
        "path": cid_path(normalized) or "",
        "meta_url": url_for("main.meta_route", requested_path=normalized),
        "edit_url": url_for("main.edit_cid", cid_prefix=normalized),
    }


def _dedupe(entries: Iterable[Dict[str, str]], key: str) -> List[Dict[str, str]]:
    seen = set()
    unique: List[Dict[str, str]] = []
    for entry in entries:
        identifier = entry.get(key)
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        unique.append(entry)
    return unique


def _discover_alias_references(text: str, aliases: Sequence[str]) -> List[Dict[str, str]]:
    matches: List[Dict[str, str]] = []
    for name in aliases:
        pattern = re.compile(rf"/{re.escape(name)}{_NAME_BOUNDARY}")
        if pattern.search(text):
            matches.append(_build_alias_reference(name))
    return _dedupe(matches, "name")


def _discover_server_references(text: str, servers: Sequence[str]) -> List[Dict[str, str]]:
    matches: List[Dict[str, str]] = []
    for name in servers:
        patterns = [
            re.compile(rf"/servers/{re.escape(name)}{_NAME_BOUNDARY}"),
            re.compile(rf"/{re.escape(name)}{_NAME_BOUNDARY}"),
        ]
        if any(pattern.search(text) for pattern in patterns):
            matches.append(_build_server_reference(name))
    return _dedupe(matches, "name")


def _discover_cid_references(text: str) -> List[Dict[str, str]]:
    candidates = {
        format_cid(match.group(1))
        for match in CID_PATH_CAPTURE_PATTERN.finditer(text)
        if is_probable_cid_component(match.group(1))
    }
    candidates = {value for value in candidates if value}
    if not candidates:
        return []

    paths = {cid_path(candidate) for candidate in candidates if cid_path(candidate)}
    if not paths:
        return []

    records = get_cids_by_paths(paths)
    matched = {format_cid(getattr(record, "path", "")) for record in records if getattr(record, "path", None)}
    references = [_build_cid_reference(value) for value in matched if value]
    return _dedupe(references, "cid")


def extract_references_from_text(text: Optional[str]) -> ReferenceMap:
    """Return aliases, servers, and CIDs referenced within text content."""

    if not text:
        return _empty_reference_map()

    snippet = text if len(text) <= _MAX_SCAN_LENGTH else text[:_MAX_SCAN_LENGTH]

    references = _empty_reference_map()

    # No user scoping needed - get all aliases and servers
    alias_names = [alias.name for alias in get_aliases()]
    server_names = [server.name for server in get_servers()]

    if alias_names:
        references["aliases"] = _discover_alias_references(snippet, alias_names)
    if server_names:
        references["servers"] = _discover_server_references(snippet, server_names)

    references["cids"] = _discover_cid_references(snippet)
    return references


def extract_references_from_bytes(data: Optional[bytes]) -> ReferenceMap:
    """Decode bytes content and extract entity references."""

    if not data:
        return _empty_reference_map()

    text = data.decode("utf-8", errors="ignore")
    return extract_references_from_text(text)


def extract_references_from_target(target_path: Optional[str]) -> ReferenceMap:
    """Extract references from a single target path, such as an alias destination."""

    references = _empty_reference_map()
    normalized_path = _normalize_local_path(target_path)
    if not normalized_path:
        return references

    alias_identifier = normalized_path.lstrip("/")
    alias = get_alias_by_name(alias_identifier)
    if not alias and alias_identifier.startswith("aliases/"):
        _, alias_name = alias_identifier.split("/", 1)
        if alias_name:
            alias = get_alias_by_name(alias_name)
    if alias:
        references["aliases"].append(_build_alias_reference(alias.name))

    server_name = _server_name_from_path(normalized_path)
    if server_name:
        server = get_server_by_name(server_name)
        if server:
            references["servers"].append(_build_server_reference(server.name))

    cid_reference = _cid_reference_from_path(normalized_path)
    if cid_reference:
        references["cids"].append(cid_reference)

    return references


def _server_name_from_path(path: str) -> Optional[str]:
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return None

    if segments[0] == "servers" and len(segments) >= 2:
        return segments[1]

    return segments[0]


def _cid_reference_from_path(path: str) -> Optional[Dict[str, str]]:
    base = _strip_extension(path)
    candidate = format_cid(base)
    if not candidate:
        return None

    cid_record_path = cid_path(candidate)
    record = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not record:
        return None

    return _build_cid_reference(candidate)


__all__ = [
    "extract_references_from_bytes",
    "extract_references_from_target",
    "extract_references_from_text",
]
