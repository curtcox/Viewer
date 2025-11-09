"""Path normalization and utility functions for meta route."""
from __future__ import annotations

from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlsplit


def normalize_target_path(requested_path: str) -> str:
    """Convert the requested metadata path into an absolute target path."""
    if not requested_path:
        return "/"

    stripped = requested_path.strip()
    if not stripped:
        return "/"

    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    return stripped


def dedupe_links(links: Iterable[str]) -> List[str]:
    """Return links without duplicates while preserving order."""
    seen: set[str] = set()
    result: List[str] = []
    for link in links:
        if not link or link in seen:
            continue
        seen.add(link)
        result.append(link)
    return result


def extract_alias_name(path: str) -> Optional[str]:
    """Return the alias segment from a path."""
    if not path or not path.startswith("/"):
        return None
    remainder = path[1:]
    if not remainder:
        return None
    return remainder.split("/", 1)[0]


def normalize_alias_target_path(target: Optional[str]) -> Optional[str]:
    """Return a normalized local path for an alias target if available."""
    if not target:
        return None

    stripped = target.strip()
    if not stripped:
        return None

    parsed = urlsplit(stripped)
    if parsed.scheme or parsed.netloc:
        return None

    candidate = parsed.path or ""
    if not candidate:
        return None

    if not candidate.startswith("/"):
        candidate = f"/{candidate}"

    return candidate


def split_extension(path: str) -> Tuple[str, Optional[str]]:
    """Return the base path and optional extension."""
    if "/" in path:
        last_segment = path.rsplit("/", 1)[-1]
    else:
        last_segment = path

    if "." in last_segment:
        base, extension = path.rsplit(".", 1)
        return base, extension
    return path, None
