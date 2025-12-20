# ruff: noqa: F821, F706
"""AI request editor server for inspecting and adjusting AI payloads."""

import html
import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from history_filters import format_history_timestamp

DEFAULT_TARGET = "/ai"
FIELD_NAMES = (
    "request_text",
    "original_text",
    "target_label",
    "context_data",
    "form_summary",
)


def _load_resource_file(filename: str) -> str:
    """Load a resource file located next to this server definition."""

    from pathlib import Path
    import os

    try:
        server_dir = Path(__file__).parent
    except NameError:
        cwd = Path(os.getcwd())
        server_dir = cwd / "reference_templates" / "servers" / "definitions"

    file_path = server_dir / filename
    with open(file_path, "r", encoding="utf-8") as handle:
        return handle.read()


def _coerce_json_value(value: Any, *, empty_fallback: Any) -> Any:
    """Convert JSON-like strings into Python objects when possible."""

    if value is None:
        return empty_fallback

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return empty_fallback
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value

    return value


def _normalize_payload(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all expected fields are present and well-formed."""

    normalized: Dict[str, Any] = {}
    for field in FIELD_NAMES:
        value = raw_payload.get(field)
        if field in {"context_data", "form_summary"}:
            normalized[field] = _coerce_json_value(value, empty_fallback={})
        else:
            normalized[field] = "" if value is None else value
    return normalized


def _extract_payload(request) -> Tuple[Dict[str, Any], str]:
    """Pull payload details and target endpoint from the incoming request."""

    if request is None:
        return _normalize_payload({}), DEFAULT_TARGET

    payload: Dict[str, Any] = {}
    target_endpoint = DEFAULT_TARGET

    json_payload = None

    if isinstance(request, dict):
        json_payload = request.get("json")
        form = request.get("form_data") or {}
    else:
        if hasattr(request, "get_json"):
            json_payload = request.get_json(silent=True)
        form = getattr(request, "form", None)

    if json_payload is not None and not isinstance(json_payload, dict):
        raise ValueError("The AI editor expects a JSON object payload.")

    if isinstance(json_payload, dict):
        payload.update(json_payload)
        target_endpoint = json_payload.get("target_endpoint", target_endpoint)

    if form:
        payload_blob = form.get("payload")
        if payload_blob:
            try:
                parsed_blob = json.loads(payload_blob)
                if not isinstance(parsed_blob, dict):
                    raise ValueError(
                        "The 'payload' form field must contain a JSON object."
                    )
                payload.update(parsed_blob)
                target_endpoint = parsed_blob.get("target_endpoint", target_endpoint)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "The AI editor could not parse the payload form field as JSON."
                ) from exc

        for field in FIELD_NAMES:
            if field in form:
                payload[field] = form.get(field)
        target_endpoint = form.get("target_endpoint", target_endpoint)

    payload = _normalize_payload(payload)
    return payload, target_endpoint or DEFAULT_TARGET


def _build_meta_links(request_path: str) -> Dict[str, str]:
    """Construct metadata links that mirror the main Viewer navigation."""

    from urllib.parse import quote_plus

    stripped = (request_path or "/").strip("/")
    requested_path = f"{stripped}.html" if stripped else ".html"

    loaded_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    timestamp_param = format_history_timestamp(loaded_at)
    encoded_timestamp = quote_plus(timestamp_param)

    return {
        "meta": f"/meta/{requested_path}",
        "history": f"/history?start={encoded_timestamp}",
        "server_events": f"/server_events?start={encoded_timestamp}",
    }


def _get_html_page(
    payload: Dict[str, Any], *, target_endpoint: str, request_path: str
) -> str:
    """Generate the AI editor HTML page with embedded resources."""

    html_template = _load_resource_file("ai_editor.html")
    css_content = _load_resource_file("ai_editor.css")
    js_content = _load_resource_file("ai_editor.js")

    css_tag = f"<style>\n{css_content}\n</style>"
    js_tag = f"<script>\n{js_content}\n</script>"

    payload_json = json.dumps(payload, ensure_ascii=False)
    target_json = json.dumps(target_endpoint or DEFAULT_TARGET)
    payload_attr = html.escape(payload_json, quote=True)
    target_attr = html.escape(target_endpoint or DEFAULT_TARGET, quote=True)

    meta_links = _build_meta_links(request_path)

    html_output = html_template.replace("{{CSS_CONTENT}}", css_tag)
    html_output = html_output.replace("{{JS_CONTENT}}", js_tag)
    html_output = html_output.replace("{{INITIAL_PAYLOAD_JSON}}", payload_json)
    html_output = html_output.replace("{{TARGET_ENDPOINT_JSON}}", target_json)
    html_output = html_output.replace("{{INITIAL_PAYLOAD_ATTR}}", payload_attr)
    html_output = html_output.replace("{{TARGET_ENDPOINT_ATTR}}", target_attr)
    html_output = html_output.replace(
        "{{META_INSPECTOR_URL}}", html.escape(meta_links["meta"])
    )
    html_output = html_output.replace(
        "{{HISTORY_SINCE_URL}}", html.escape(meta_links["history"])
    )
    html_output = html_output.replace(
        "{{SERVER_EVENTS_SINCE_URL}}", html.escape(meta_links["server_events"])
    )

    return html_output


def main(input_data=None, *, request=None, context=None):
    """Entry point for the AI request editor server."""

    if input_data is not None:
        return {
            "output": "The AI request editor cannot be used in a server chain. Access it directly at /ai_editor.",
            "content_type": "text/plain",
            "status": 400,
        }

    try:
        if isinstance(request, dict):
            request_path = request.get("path", "/ai_editor")
        else:
            request_path = (
                getattr(request, "path", "/ai_editor") if request else "/ai_editor"
            )
        payload, target_endpoint = _extract_payload(request)

        html_content = _get_html_page(
            payload, target_endpoint=target_endpoint, request_path=request_path
        )

        return {
            "output": html_content,
            "content_type": "text/html",
        }
    except ValueError as exc:
        message = (
            "Unable to render the AI editor because the request parameters were invalid.\n"
            f"Details: {exc}"
        )
        return {
            "output": message,
            "content_type": "text/plain",
            "status": 400,
        }
