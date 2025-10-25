"""Helpers for attaching artifacts to Gauge reports."""

from __future__ import annotations

import asyncio
import base64
import html
import io
import json
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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
_ARTIFACT_DIR_FALLBACK = "reports/html-report/secureapp-artifacts"


def attach_response_snapshot(response: Any, label: str | None = None) -> None:
    """Capture the response as a browser screenshot and JSON payload."""

    if Messages is None or response is None:
        return

    try:
        body_text = response.get_data(as_text=True)  # type: ignore[attr-defined]
        body_bytes = response.get_data()  # type: ignore[attr-defined]
    except TypeError:
        body_bytes = response.get_data()  # type: ignore[attr-defined]
        body_text = body_bytes.decode("utf-8", errors="replace")

    request = getattr(response, "request", None)
    method = getattr(request, "method", "GET")
    path = getattr(request, "path", "<unknown>")
    status_code = getattr(response, "status_code", "?")
    resolved_label = label or f"{method} {path}"

    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    preview_text = _prepare_preview_text(body_text)

    screenshot_bytes: bytes | None = None
    if _looks_like_html(response, body_text):
        html_document = _prepare_html_document(body_text)
        screenshot_bytes = _render_browser_screenshot(html_document)

    if screenshot_bytes is None:
        screenshot_bytes = _render_text_image(resolved_label, str(status_code), preview_text)

    base_name = _build_base_filename(resolved_label)
    artifact_dir = _ensure_artifact_directory()
    png_path = artifact_dir / f"{base_name}.png"
    png_path.write_bytes(screenshot_bytes)

    metadata = _build_metadata(
        response=response,
        request=request,
        label=resolved_label,
        timestamp=timestamp,
        preview_text=preview_text,
        body_bytes=body_bytes,
    )
    json_path = artifact_dir / f"{base_name}.json"
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    _attach_file(png_path, "image/png")
    _attach_file(json_path, "application/json")

    snippet = textwrap.dedent(
        f"""
        <details class=\"secureapp-screenshot\">
          <summary>Screenshot: {html.escape(resolved_label)}</summary>
          <p>
            <a href="{png_path.name}" target="_blank" rel="noopener">Open screenshot</a>
            •
            <a href="{json_path.name}" target="_blank" rel="noopener">View request/response JSON</a>
          </p>
          <img src="{png_path.name}" alt="{html.escape(resolved_label)}" style="max-width: 100%; border: 1px solid #d0d7de; border-radius: 6px; box-shadow: 0 1px 3px rgba(27, 31, 36, 0.15);" />
        </details>
        """
    ).strip()

    if hasattr(Messages, "write_message"):
        try:
            Messages.write_message(snippet)  # type: ignore[attr-defined]
        except TypeError:
            Messages.write_message(f"Saved response snapshot to {png_path}")  # type: ignore[attr-defined]


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


def _build_base_filename(label: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", label).strip("-")
    if not sanitized:
        sanitized = "response"
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique = uuid4().hex[:8]
    filename = f"{sanitized}-{timestamp}-{unique}"
    return filename[:240]


def _ensure_artifact_directory() -> Path:
    directory = Path(os.environ.get("GAUGE_ARTIFACT_DIR", _ARTIFACT_DIR_FALLBACK))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _attach_file(path: Path, mime_type: str) -> None:
    if not path.exists():
        return

    data = path.read_bytes()

    if hasattr(Messages, "attach_binary"):
        Messages.attach_binary(data, mime_type, path.name)  # type: ignore[attr-defined]
    elif hasattr(Messages, "add_attachment"):
        Messages.add_attachment(str(path))  # type: ignore[attr-defined]
    elif hasattr(Messages, "write_message"):
        Messages.write_message(f"Saved response snapshot to {path}")  # type: ignore[attr-defined]


def _build_metadata(
    *,
    response: Any,
    request: Any,
    label: str,
    timestamp: str,
    preview_text: str,
    body_bytes: bytes,
) -> dict[str, Any]:
    request_headers = _serialize_headers(getattr(request, "headers", None))
    response_headers = _serialize_headers(getattr(response, "headers", None))

    request_body = None
    if request is not None and hasattr(request, "get_data"):
        try:
            request_body = request.get_data()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - best effort capture
            request_body = None

    response_body = body_bytes

    query: dict[str, Any] = {}
    if request is not None:
        args = getattr(request, "args", None)
        if args is not None:
            try:
                query = args.to_dict(flat=False)  # type: ignore[call-arg]
            except TypeError:
                query = dict(args)

    metadata: dict[str, Any] = {
        "label": label,
        "captured_at": timestamp,
        "preview": preview_text,
        "request": {
            "method": getattr(request, "method", None),
            "path": getattr(request, "full_path", getattr(request, "path", None)),
            "url": getattr(request, "url", None),
            "headers": request_headers,
            "query": query,
            "body": _coerce_body(request_body),
        },
        "response": {
            "status_code": getattr(response, "status_code", None),
            "mimetype": getattr(response, "mimetype", None),
            "headers": response_headers,
            "body": _coerce_body(response_body),
        },
    }

    return metadata


def _serialize_headers(headers: Any) -> list[dict[str, str]]:
    if headers is None:
        return []

    items: list[tuple[Any, Any]]
    try:
        items = list(headers.items(multi=True))  # type: ignore[attr-defined]
    except TypeError:
        try:
            items = list(headers.items())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            items = []

    result: list[dict[str, str]] = []
    for key, value in items:
        result.append({"name": str(key), "value": str(value)})
    return result


def _coerce_body(data: Any) -> dict[str, Any] | None:
    if data is None:
        return None

    if isinstance(data, str):
        return {"encoding": "utf-8", "text": data}

    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
            return {"encoding": "utf-8", "text": text}
        except UnicodeDecodeError:
            encoded = base64.b64encode(data).decode("ascii")
            return {"encoding": "base64", "data": encoded}

    return {"encoding": "repr", "text": repr(data)}


def _looks_like_html(response: Any, body_text: str) -> bool:
    mimetype = getattr(response, "mimetype", "") or ""
    if "html" in mimetype:
        return True
    snippet = body_text.strip().lower()
    return snippet.startswith("<!doctype") or snippet.startswith("<html")


def _prepare_html_document(html_text: str) -> str:
    with_css = _inline_stylesheets(html_text)
    return _rewrite_asset_sources(with_css)


def _inline_stylesheets(html_text: str) -> str:
    root = Path(__file__).resolve().parents[1]

    def replace(match: re.Match[str]) -> str:
        href = match.group("href")
        if not href:
            return match.group(0)
        stylesheet_path = _resolve_asset_path(root, href)
        if stylesheet_path is None or not stylesheet_path.exists():
            return match.group(0)
        try:
            css_text = stylesheet_path.read_text(encoding="utf-8")
        except OSError:
            return match.group(0)
        return f"<style>{css_text}</style>"

    pattern = re.compile(
        r"<link[^>]+rel=[\"']stylesheet[\"'][^>]*href=[\"'](?P<href>[^\"']+)[\"'][^>]*>",
        re.IGNORECASE,
    )
    return re.sub(pattern, replace, html_text)


def _rewrite_asset_sources(html_text: str) -> str:
    root = Path(__file__).resolve().parents[1]

    def replace(match: re.Match[str]) -> str:
        prefix, value = match.group("prefix"), match.group("value")
        asset_path = _resolve_asset_path(root, value)
        if asset_path is None or not asset_path.exists():
            return match.group(0)
        return f'{prefix}="{asset_path.as_uri()}"'

    pattern = re.compile(
        r"(?P<prefix>\b(?:src|href))=\"(?P<value>[^\"]+)\"",
        re.IGNORECASE,
    )
    return re.sub(pattern, replace, html_text)


def _resolve_asset_path(root: Path, href: str) -> Path | None:
    if not href:
        return None
    clean_href = href.split("?", 1)[0].split("#", 1)[0]
    if clean_href.startswith("http://") or clean_href.startswith("https://"):
        return None
    if clean_href.startswith("data:"):
        return None

    relative = clean_href.lstrip("/")
    candidate = root / relative
    if candidate.exists():
        return candidate
    return None


def _render_browser_screenshot(html_document: str) -> bytes | None:
    try:
        from pyppeteer import launch
    except ImportError:  # pragma: no cover - optional dependency in tests
        return None

    async def _capture() -> bytes:
        browser = await launch(
            headless=True,
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        try:
            page = await browser.newPage()
            await page.setViewport({"width": _IMAGE_WIDTH, "height": 720})
            try:
                await page.setContent(html_document, waitUntil="networkidle0")
            except TypeError:
                await page.setContent(html_document)
                wait_for_function = getattr(page, "waitForFunction", None)
                if callable(wait_for_function):
                    await wait_for_function("document.readyState === 'complete'")
            return await page.screenshot(fullPage=True)
        finally:
            await browser.close()

    try:
        return asyncio.run(_capture())
    except (RuntimeError, OSError, Exception):  # Catch Chromium download failures and other errors
        try:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(_capture())
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                asyncio.set_event_loop(None)
        except Exception:  # If browser still fails, fall back to text rendering
            return None

