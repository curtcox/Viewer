# ruff: noqa: F821, F706
"""Generate QR code PNGs from chained input or literal path text."""

from typing import Any, Optional

from content_serving import generate_qr_png


def _coerce_text(value: Any) -> Optional[str]:
    """Normalize arbitrary input to a non-empty string when possible."""

    if value is None:
        return None

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            value = value.decode("utf-8", errors="replace")

    text = str(value)
    normalized = text.strip()
    return normalized or None


def _extract_path_suffix(request: Any) -> Optional[str]:
    """Return the portion of the request path after /qr/ for fallback use."""

    if not isinstance(request, dict):
        return None

    path = request.get("path") or ""
    prefix = "/qr"
    if not path.startswith(prefix):
        return None

    suffix = path[len(prefix) :].lstrip("/")
    return suffix or None


def main(text: Any = None, *, request=None):
    """Render a QR code PNG from chained input or literal path text."""

    qr_text = _coerce_text(text) or _extract_path_suffix(request)
    if not qr_text:
        return {
            "output": "Provide QR content via /qr/<text> or chained server output.",
            "content_type": "text/plain",
            "status": 400,
        }

    try:
        png_bytes = generate_qr_png(qr_text)
    except RuntimeError as exc:
        return {
            "output": str(exc),
            "content_type": "text/plain",
            "status": 500,
        }

    return {"output": png_bytes, "content_type": "image/png"}
