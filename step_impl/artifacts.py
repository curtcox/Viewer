"""Helpers for attaching artifacts to Gauge reports."""

from __future__ import annotations

import io
import re
import textwrap
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:  # pragma: no cover - exercised under the real Gauge runner in CI
    from getgauge.python import Messages
except ImportError:  # pragma: no cover - fallback for the local Gauge stub
    try:
        from gauge_stub.python import Messages  # type: ignore
    except ImportError:
        Messages = None  # type: ignore


_MAX_BODY_PREVIEW_CHARS = 1200
_IMAGE_WIDTH = 1280
_MARGIN = 24
_LINE_SPACING = 6


def attach_response_snapshot(response: Any, label: str | None = None) -> None:
    """Render the Flask response body into a PNG and attach it to the report."""

    if Messages is None:
        return

    if response is None:
        return

    try:
        body_text = response.get_data(as_text=True)  # type: ignore[attr-defined]
    except TypeError:
        raw_bytes = response.get_data()  # type: ignore[attr-defined]
        body_text = raw_bytes.decode("utf-8", errors="replace")

    request = getattr(response, "request", None)
    method = getattr(request, "method", "GET")
    path = getattr(request, "path", "<unknown>")

    status_code = getattr(response, "status_code", "?")
    resolved_label = label or f"{method} {path}"

    preview_text = _prepare_preview_text(body_text)
    image_bytes = _render_text_image(resolved_label, str(status_code), preview_text)
    filename = _build_filename(resolved_label)

    Messages.attach_binary(image_bytes, "image/png", filename)  # type: ignore[attr-defined]


def _prepare_preview_text(body_text: str) -> str:
    cleaned = "\n".join(line.rstrip() for line in body_text.splitlines())
    snippet = cleaned[:_MAX_BODY_PREVIEW_CHARS]
    return snippet


def _render_text_image(label: str, status_code: str, preview_text: str) -> bytes:
    font = ImageFont.load_default()
    lines: list[str] = []

    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    lines.append(f"{label}")
    lines.append(f"Status: {status_code}  •  Captured: {timestamp}")
    lines.append("")
    lines.append("Body preview:")

    wrapped_preview = textwrap.wrap(preview_text, width=150)
    if wrapped_preview:
        lines.extend(wrapped_preview)
    else:
        lines.append("<empty response body>")

    ascent, descent = font.getmetrics()
    line_height = ascent + descent + _LINE_SPACING
    height = (_MARGIN * 2) + max(1, len(lines)) * line_height

    image = Image.new("RGB", (_IMAGE_WIDTH, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    y = _MARGIN
    for line in lines:
        draw.text((_MARGIN, y), line, fill=(28, 28, 30), font=font)
        y += line_height

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _build_filename(label: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", label).strip("-")
    if not sanitized:
        sanitized = "response"
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{sanitized}-{timestamp}.png"
    return filename[:255]

