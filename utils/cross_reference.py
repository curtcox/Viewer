"""Cross-reference data building utilities for entity relationship tracking."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from flask import url_for

from cid_presenter import cid_path, format_cid, format_cid_short
from constants import TYPE_LABELS
from db_access import get_aliases, get_cids_by_paths, get_servers
from models import CID
from utils.dom_keys import _entity_key, _reference_key


# Import these functions via a late import to avoid circular dependency
# and to allow tests to mock them at routes.core level
def _get_ref_dependencies():
    """Late import to avoid circular dependency with routes.core."""
    import routes.core as core

    return (
        core.get_primary_alias_route,
        core.extract_references_from_target,
        core.extract_references_from_text,
        core.extract_references_from_bytes,
    )


@dataclass
class PreviewResult:
    """Result of text preview extraction."""

    text: str
    was_truncated: bool


def _preview_text_from_bytes(data: Optional[bytes]) -> PreviewResult:
    """
    Extract a compact preview from byte data.

    Args:
        data: The byte data to preview

    Returns:
        PreviewResult containing the preview text and truncation flag
    """
    if not data:
        return PreviewResult("", False)

    try:
        snippet = data.decode("utf-8", errors="replace")
        preview = snippet[:20].replace("\n", " ").replace("\r", " ")
        return PreviewResult(preview, len(snippet) > 20)
    except (UnicodeDecodeError, AttributeError):
        # Fall back to hex preview for non-text data
        hex_preview = data[:10].hex()
        return PreviewResult(hex_preview, len(data or b"") > 10)


def _entity_url(entity_type: str, identifier: str) -> Optional[str]:
    """
    Return the canonical URL for viewing the given entity.

    Args:
        entity_type: The type of entity (e.g., 'alias', 'server', 'cid')
        identifier: The unique identifier for the entity

    Returns:
        The URL for viewing the entity, or None if not applicable
    """
    if not identifier:
        return None

    if entity_type == "alias":
        return url_for("main.view_alias", alias_name=identifier)
    if entity_type == "server":
        return url_for("main.view_server", server_name=identifier)
    if entity_type == "cid":
        normalized = format_cid(identifier)
        if not normalized:
            return None
        return url_for("main.meta_route", requested_path=normalized)
    return None


@dataclass
class CrossReferenceState:
    """Track entities, relationships, and references while building the dashboard."""

    entity_implied: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    entity_outgoing_refs: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    entity_incoming_refs: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    referenced_cids: Set[str] = field(default_factory=set)
    references: List[Dict[str, Any]] = field(default_factory=list)
    reference_seen: Set[Tuple[str, str, str, str]] = field(default_factory=set)

    def record_cid(self, entry: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Normalize a CID reference and add it to the known set.

        Args:
            entry: Dictionary containing 'cid' key

        Returns:
            The normalized CID value or None
        """
        if not entry:
            return None

        cid_value = format_cid(entry.get("cid"))
        if not cid_value:
            return None

        self.referenced_cids.add(cid_value)
        return cid_value

    def register_reference(
        self,
        source_type: str,
        source_identifier: str,
        target_type: str,
        target_identifier: str,
    ) -> None:
        """
        Record a relationship between two entities, enforcing uniqueness.

        Args:
            source_type: The type of the source entity
            source_identifier: The identifier of the source entity
            target_type: The type of the target entity
            target_identifier: The identifier of the target entity
        """
        if not source_identifier or not target_identifier:
            return

        source_key = _entity_key(source_type, source_identifier)
        target_key = _entity_key(target_type, target_identifier)
        dedupe_key = (source_type, source_identifier, target_type, target_identifier)
        if dedupe_key in self.reference_seen:
            return
        self.reference_seen.add(dedupe_key)

        ref_key = _reference_key(source_key, target_key)

        self.references.append(
            {
                "key": ref_key,
                "source_key": source_key,
                "target_key": target_key,
                "source_type": source_type,
                "target_type": target_type,
                "source_label": TYPE_LABELS.get(source_type, source_type.title()),
                "target_label": TYPE_LABELS.get(target_type, target_type.title()),
                "source_name": source_identifier,
                "target_name": target_identifier,
                "source_url": _entity_url(source_type, source_identifier),
                "target_url": _entity_url(target_type, target_identifier),
                "source_cid_short": format_cid_short(source_identifier)
                if source_type == "cid"
                else None,
                "target_cid_short": format_cid_short(target_identifier)
                if target_type == "cid"
                else None,
            }
        )

        self.entity_implied[source_key].add(target_key)
        if source_key != target_key:
            self.entity_implied[target_key].add(source_key)
        self.entity_outgoing_refs[source_key].add(ref_key)
        self.entity_incoming_refs[target_key].add(ref_key)


def _register_alias_or_server_refs(
    state: CrossReferenceState,
    source_type: str,
    source_name: str,
    refs: Optional[Dict[str, Any]],
) -> None:
    """
    Register references found in alias or server definitions.

    Args:
        state: The cross-reference state to update
        source_type: The type of the source entity ('alias' or 'server')
        source_name: The name of the source entity
        refs: Dictionary containing 'aliases', 'servers', and 'cids' lists
    """
    refs = refs or {}

    for ref in refs.get("aliases", []):
        target_name = ref.get("name")
        if target_name:
            state.register_reference(source_type, source_name, "alias", target_name)

    for ref in refs.get("servers", []):
        target_name = ref.get("name")
        if target_name:
            state.register_reference(source_type, source_name, "server", target_name)

    for ref in refs.get("cids", []):
        cid_value = state.record_cid(ref)
        if cid_value:
            state.register_reference(source_type, source_name, "cid", cid_value)


def _register_cid_refs(
    state: CrossReferenceState,
    cid_value: str,
    refs: Optional[Dict[str, Any]],
) -> None:
    """
    Register references extracted from CID file content.

    Args:
        state: The cross-reference state to update
        cid_value: The CID value
        refs: Dictionary containing 'aliases', 'servers', and 'cids' lists
    """
    refs = refs or {}

    for ref in refs.get("aliases", []):
        target_name = ref.get("name")
        if target_name:
            state.register_reference("cid", cid_value, "alias", target_name)

    for ref in refs.get("servers", []):
        target_name = ref.get("name")
        if target_name:
            state.register_reference("cid", cid_value, "server", target_name)

    for ref in refs.get("cids", []):
        target_cid = format_cid(ref.get("cid"))
        if target_cid and target_cid in state.referenced_cids:
            state.register_reference("cid", cid_value, "cid", target_cid)


def _collect_alias_entries(state: CrossReferenceState) -> List[Dict[str, Any]]:
    """
    Collect all alias entries and register their references.

    Args:
        state: The cross-reference state to update

    Returns:
        List of alias entry dictionaries
    """
    get_primary_alias_route, extract_references_from_target, _, _ = (
        _get_ref_dependencies()
    )

    aliases = get_aliases()
    alias_entries: List[Dict[str, Any]] = []

    for alias in aliases:
        primary_route = get_primary_alias_route(alias)
        target_path = primary_route.target_path if primary_route else None
        alias_entries.append(
            {
                "type": "alias",
                "name": alias.name,
                "url": url_for("main.view_alias", alias_name=alias.name),
                "entity_key": _entity_key("alias", alias.name),
                "target_path": target_path or "",
            }
        )

        refs = extract_references_from_target(target_path)
        _register_alias_or_server_refs(state, "alias", alias.name, refs)

    return alias_entries


def _collect_server_entries(state: CrossReferenceState) -> List[Dict[str, Any]]:
    """
    Collect all server entries and register their references.

    Args:
        state: The cross-reference state to update

    Returns:
        List of server entry dictionaries
    """
    _, _, extract_references_from_text, _ = _get_ref_dependencies()

    servers = get_servers()
    server_entries: List[Dict[str, Any]] = []

    for server in servers:
        definition_cid = format_cid(getattr(server, "definition_cid", ""))
        server_entries.append(
            {
                "type": "server",
                "name": server.name,
                "url": url_for("main.view_server", server_name=server.name),
                "entity_key": _entity_key("server", server.name),
                "definition_cid": definition_cid,
            }
        )

        refs = extract_references_from_text(getattr(server, "definition", ""))
        _register_alias_or_server_refs(state, "server", server.name, refs)

        if definition_cid:
            state.referenced_cids.add(definition_cid)
            state.register_reference("server", server.name, "cid", definition_cid)

    return server_entries


def _collect_cid_entries(
    state: CrossReferenceState,
    alias_keys: Set[str],
    server_keys: Set[str],
) -> List[Dict[str, Any]]:
    """
    Collect all CID entries and register their references.

    Args:
        state: The cross-reference state to update
        alias_keys: Set of alias entity keys
        server_keys: Set of server entity keys

    Returns:
        List of CID entry dictionaries (filtered to those with named entity relationships)
    """
    _, _, _, extract_references_from_bytes = _get_ref_dependencies()

    cid_paths_list: List[str] = []
    for value in state.referenced_cids:
        path_value = cid_path(value)
        if path_value:
            cid_paths_list.append(path_value)

    records_by_cid: Dict[str, CID] = {}
    if cid_paths_list:
        cid_records = get_cids_by_paths(cid_paths_list)
        records_by_cid = {
            format_cid(getattr(record, "path", "")): record
            for record in cid_records
            if getattr(record, "path", None)
        }

    cid_candidates: List[Dict[str, Any]] = []
    for cid_value in sorted(state.referenced_cids):
        record = records_by_cid.get(cid_value)
        file_data = getattr(record, "file_data", None) if record else None
        preview_result = _preview_text_from_bytes(file_data)

        cid_entry = {
            "type": "cid",
            "cid": cid_value,
            "entity_key": _entity_key("cid", cid_value),
            "preview": preview_result.text,
            "preview_truncated": preview_result.was_truncated,
            "short_label": format_cid_short(cid_value),
            "meta_url": _entity_url("cid", cid_value),
        }

        if file_data:
            refs = extract_references_from_bytes(file_data)
            _register_cid_refs(state, cid_value, refs)

        cid_candidates.append(cid_entry)

    # Filter CIDs to only those with named entity relationships
    named_entity_keys = alias_keys | server_keys
    cid_entries: List[Dict[str, Any]] = []

    for cid_entry in cid_candidates:
        cid_key = cid_entry["entity_key"]
        related_keys = state.entity_implied.get(cid_key, set())
        has_named_relation = any(key in named_entity_keys for key in related_keys)
        related_reference_keys = state.entity_outgoing_refs.get(
            cid_key, set()
        ) | state.entity_incoming_refs.get(cid_key, set())

        if not has_named_relation or not related_reference_keys:
            continue

        cid_entries.append(cid_entry)

    return cid_entries


def _filter_references(
    state: CrossReferenceState,
    all_entity_keys: Set[str],
) -> List[Dict[str, Any]]:
    """
    Filter references to only those between existing entities.

    Args:
        state: The cross-reference state
        all_entity_keys: Set of all entity keys to include

    Returns:
        List of filtered reference dictionaries
    """
    filtered_references: List[Dict[str, Any]] = []
    reference_keys_by_source: Dict[str, Set[str]] = defaultdict(set)
    reference_keys_by_target: Dict[str, Set[str]] = defaultdict(set)

    for ref in state.references:
        if (
            ref["source_key"] not in all_entity_keys
            or ref["target_key"] not in all_entity_keys
        ):
            continue
        filtered_references.append(ref)
        reference_keys_by_source[ref["source_key"]].add(ref["key"])
        reference_keys_by_target[ref["target_key"]].add(ref["key"])

    return filtered_references, reference_keys_by_source, reference_keys_by_target


def _assemble_response(
    alias_entries: List[Dict[str, Any]],
    server_entries: List[Dict[str, Any]],
    cid_entries: List[Dict[str, Any]],
    filtered_references: List[Dict[str, Any]],
    *,
    state: CrossReferenceState,
    all_entity_keys: Set[str],
    reference_keys_by_source: Dict[str, Set[str]],
    reference_keys_by_target: Dict[str, Set[str]],
) -> Dict[str, Any]:
    """
    Assemble the final cross-reference data structure.

    Args:
        alias_entries: List of alias entries
        server_entries: List of server entries
        cid_entries: List of CID entries
        filtered_references: List of filtered references
        state: The cross-reference state
        all_entity_keys: Set of all entity keys
        reference_keys_by_source: Mapping of entity keys to outgoing reference keys
        reference_keys_by_target: Mapping of entity keys to incoming reference keys

    Returns:
        Dictionary containing all cross-reference data
    """
    # Add metadata to each entry
    for entry in alias_entries + server_entries + cid_entries:
        key = entry["entity_key"]
        entry["implied_keys"] = sorted(
            key_value
            for key_value in state.entity_implied.get(key, [])
            if key_value in all_entity_keys
        )
        entry["outgoing_refs"] = sorted(reference_keys_by_source.get(key, []))
        entry["incoming_refs"] = sorted(reference_keys_by_target.get(key, []))

    # Sort references for consistent display
    filtered_references.sort(
        key=lambda item: (
            item["source_label"],
            item["source_name"],
            item["target_label"],
            item["target_name"],
        )
    )

    return {
        "aliases": alias_entries,
        "servers": server_entries,
        "cids": cid_entries,
        "references": filtered_references,
    }


def build_cross_reference_data() -> Dict[str, Any]:
    """
    Build cross-reference dashboard data showing relationships between entities.

    This function:
    1. Collects all aliases, servers, and referenced CIDs
    2. Extracts references between entities from their definitions
    3. Filters to show only CIDs with named entity relationships
    4. Returns structured data for template rendering with highlight metadata

    Returns:
        Dictionary with keys: 'aliases', 'servers', 'cids', 'references'
    """
    state = CrossReferenceState()

    alias_entries = _collect_alias_entries(state)
    server_entries = _collect_server_entries(state)

    alias_keys = {entry["entity_key"] for entry in alias_entries}
    server_keys = {entry["entity_key"] for entry in server_entries}

    cid_entries = _collect_cid_entries(state, alias_keys, server_keys)

    all_entity_keys = (
        alias_keys | server_keys | {entry["entity_key"] for entry in cid_entries}
    )

    filtered_refs, ref_by_src, ref_by_tgt = _filter_references(state, all_entity_keys)

    return _assemble_response(
        alias_entries,
        server_entries,
        cid_entries,
        filtered_refs,
        state=state,
        all_entity_keys=all_entity_keys,
        reference_keys_by_source=ref_by_src,
        reference_keys_by_target=ref_by_tgt,
    )
