"""CID normalization, serialization, and content encoding utilities."""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field
from typing import Any

from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid, store_cid_from_bytes
from db_access import get_cid_by_path


def normalise_cid(value: Any) -> str:
    """Normalize a CID value to a clean string format."""
    if not isinstance(value, str):
        return ''
    cleaned = value.strip()
    if not cleaned:
        return ''
    cleaned = cleaned.split('.')[0]
    return cleaned.lstrip('/')


def coerce_enabled_flag(value: Any) -> bool:
    """Return a best-effort boolean for enabled flags in import payloads."""
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'false', '0', 'off', 'no'}:
            return False
        if normalized in {'true', '1', 'on', 'yes'}:
            return True

    if isinstance(value, (int, float)):
        return bool(value)

    return True if value is None else bool(value)


def serialise_cid_value(content: bytes) -> str:
    """Serialize CID content as a UTF-8 string for export.

    Always decodes content as UTF-8. If the content contains invalid UTF-8
    sequences, they are replaced with the Unicode replacement character.
    """
    return content.decode('utf-8', errors='replace')


def format_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string."""
    units = ['bytes', 'KB', 'MB', 'GB', 'TB']
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'bytes':
                return f'{int(size)} bytes'
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{int(num_bytes)} bytes'


@dataclass
class CidWriter:
    """Helper for writing CIDs during export operations."""

    include_optional: bool
    store_content: bool
    cid_map_entries: dict[str, str] = field(default_factory=dict)

    def cid_for_content(
        self,
        content: bytes,
        *,
        optional: bool = True,
        include_in_map: bool = True,
    ) -> str:
        """Generate or store a CID for the given content."""
        if self.store_content:
            cid_value = store_cid_from_bytes(content)
        else:
            cid_value = format_cid(generate_cid(content))

        if include_in_map:
            store_cid_entry(
                cid_value,
                content,
                self.cid_map_entries,
                self.include_optional,
                optional=optional,
            )

        return cid_value


def deserialise_cid_value(raw_value: Any) -> tuple[bytes | None, str | None]:
    """Deserialize a CID value from import payload format."""
    if isinstance(raw_value, dict):
        encoding = (raw_value.get('encoding') or 'utf-8').strip().lower()
        value = raw_value.get('value')
    else:
        encoding = 'utf-8'
        value = raw_value

    if not isinstance(value, str):
        return None, 'CID map values must be strings or objects with a "value" field.'

    if encoding in ('utf-8', 'text', 'utf8'):
        return value.encode('utf-8'), None

    if encoding == 'base64':
        try:
            return base64.b64decode(value.encode('ascii')), None
        except (binascii.Error, ValueError):
            return None, 'CID map entry used invalid base64 encoding.'

    try:
        return value.encode(encoding), None
    except LookupError:
        return None, f'CID map entry specified unsupported encoding "{encoding}".'


def parse_cid_values_section(raw_map: Any) -> tuple[dict[str, bytes], list[str]]:
    """Parse a CID values section from an import payload."""
    if raw_map is None:
        return {}, []
    if not isinstance(raw_map, dict):
        return {}, ['CID map must be an object mapping CID values to content.']

    cid_values: dict[str, bytes] = {}
    errors: list[str] = []

    for raw_key, raw_value in raw_map.items():
        cid_value = normalise_cid(raw_key)
        if not cid_value:
            errors.append('CID map entries must use non-empty string keys.')
            continue

        content_bytes, error = deserialise_cid_value(raw_value)
        if error:
            errors.append(f'CID "{cid_value}" entry invalid: {error}')
            continue
        if content_bytes is None:
            errors.append(f'CID "{cid_value}" entry did not include decodable content.')
            continue

        cid_values[cid_value] = content_bytes

    return cid_values, errors


def load_cid_bytes(cid_value: str, cid_map: dict[str, bytes]) -> bytes | None:
    """Load CID content bytes from the provided map or database."""
    normalised = normalise_cid(cid_value)
    if not normalised:
        return None

    if normalised in cid_map:
        return cid_map[normalised]

    path = cid_path(normalised)
    if not path:
        return None

    record = get_cid_by_path(path)
    if record and record.file_data is not None:
        return bytes(record.file_data)

    return None


def encode_section_content(value: Any) -> bytes:
    """Encode a section value as JSON bytes."""
    return json.dumps(value, indent=2, sort_keys=True).encode('utf-8')


def load_export_section(
    payload: dict[str, Any],
    key: str,
    cid_map: dict[str, bytes],
) -> tuple[Any, list[str], bool]:
    """Load and parse an export section from payload data."""
    if key not in payload:
        return None, [], False

    raw_value = payload.get(key)
    if isinstance(raw_value, str):
        cid_value = normalise_cid(raw_value)
        if not cid_value:
            return None, [f'Section "{key}" referenced an invalid CID value.'], True
        content_bytes = load_cid_bytes(cid_value, cid_map)
        if content_bytes is None:
            return None, [
                f'Section "{key}" referenced CID "{cid_value}" but the content was not provided.'
            ], True
        try:
            decoded_text = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return None, [
                f'Section "{key}" referenced CID "{cid_value}" that was not UTF-8 encoded.'
            ], True
        try:
            return json.loads(decoded_text), [], False
        except json.JSONDecodeError:
            return None, [
                f'Section "{key}" referenced CID "{cid_value}" with invalid JSON content.'
            ], True

    return raw_value, [], False


def store_cid_entry(
    cid_value: str,
    content: bytes,
    cid_map_entries: dict[str, str],
    include_optional: bool,
    *,
    optional: bool = True,
) -> None:
    """Record a CID value for the export when it should be included."""
    if optional and not include_optional:
        return

    normalised = normalise_cid(cid_value)
    if not normalised or normalised in cid_map_entries:
        return

    cid_map_entries[normalised] = serialise_cid_value(content)
