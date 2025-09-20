"""Upload templates package for the Viewer application.

This package contains predefined content templates that can be used when uploading
new files. Each template describes metadata and the actual content to upload.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable
import json


def get_upload_templates() -> list[dict[str, Any]]:
    """Return copies of all available upload templates."""
    return list(iter_upload_templates())


def iter_upload_templates() -> Iterable[Dict[str, Any]]:
    """Yield upload templates one-by-one without exposing internal state."""
    base_dir = Path(__file__).parent
    template_dir = base_dir / "templates"

    for template_file in template_dir.glob("*.json"):
        with open(template_file, "r", encoding="utf-8") as f:
            template = json.load(f)

        if "content_file" in template:
            content_path = base_dir / template["content_file"]
            try:
                with open(content_path, "r", encoding="utf-8") as content_file:
                    template["content"] = content_file.read()
            except OSError as exc:
                print(f"Warning: Could not load content file {content_path}: {exc}")
                continue

        yield dict(template)


__all__ = ["get_upload_templates", "iter_upload_templates"]
