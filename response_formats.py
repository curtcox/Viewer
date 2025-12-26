"""Utilities for serving OpenAPI-documented routes in multiple formats."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from html import escape as html_escape, unescape as html_unescape
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, Set

from flask import Flask, Response, current_app, g, request
from werkzeug.datastructures import MIMEAccept

from routes.openapi import openapi_route_rules

SUPPORTED_FORMATS: Mapping[str, str] = {
    "html": "text/html",
    "json": "application/json",
    "txt": "text/plain",
    "md": "text/markdown",
    "xml": "application/xml",
    "csv": "text/csv",
}

ACCEPT_ALIASES: Mapping[str, str] = {
    "text/html": "html",
    "application/xhtml+xml": "html",
    "application/json": "json",
    "text/json": "json",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md",
    "application/xml": "xml",
    "text/xml": "xml",
    "text/csv": "csv",
}

_XML_TAG_RE = re.compile(r"[^0-9A-Za-z_]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_XML_INVALID_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def register_response_format_handlers(app: Flask) -> None:
    """Enable extension and Accept-based content negotiation for OpenAPI routes."""

    if app.config.get("RESPONSE_FORMAT_HANDLERS_REGISTERED"):
        return

    documented_rules = openapi_route_rules(app)
    base_rules: MutableMapping[str, _RuleDetails] = {}

    for rule in list(app.url_map.iter_rules()):
        if not rule.endpoint.startswith("main."):
            continue
        if rule.rule not in documented_rules:
            continue
        base_rules[rule.endpoint] = _RuleDetails.from_rule(rule)

    format_config = {
        "base_endpoints": set(base_rules.keys()),
        "forced_endpoints": {},
    }

    forced_endpoints: MutableMapping[str, str] = format_config["forced_endpoints"]

    for endpoint, rule_details in base_rules.items():
        for ext in SUPPORTED_FORMATS:
            ext_rule = f"{rule_details.rule}.{ext}"
            if _rule_exists(app, ext_rule):
                continue
            new_endpoint = f"{endpoint}__format_{ext}"
            app.add_url_rule(
                ext_rule,
                endpoint=new_endpoint,
                view_func=app.view_functions[endpoint],
                methods=rule_details.methods,
                defaults=rule_details.defaults,
                subdomain=rule_details.subdomain,
                strict_slashes=rule_details.strict_slashes,
                provide_automatic_options=rule_details.provide_automatic_options,
            )
            forced_endpoints[new_endpoint] = ext

    app.config["RESPONSE_FORMAT_CONFIG"] = format_config

    @app.before_request
    def _determine_response_format() -> None:
        config = current_app.config.get("RESPONSE_FORMAT_CONFIG")
        if not config:
            return

        endpoint = request.endpoint
        if endpoint is None:
            return

        forced = config["forced_endpoints"]
        if endpoint in forced:
            g.response_format = forced[endpoint]
            return

        base: Set[str] = config["base_endpoints"]
        if endpoint not in base:
            return

        prefers_json = request.is_json or request.headers.get(
            "Content-Type", ""
        ).startswith("application/json")
        if not prefers_json and request.method in {"POST", "PUT", "PATCH"}:
            prefers_json = request.is_json

        default_format = "json" if prefers_json else "html"
        g.response_format = resolve_format_from_accept(
            request.accept_mimetypes, default_format
        )

    @app.after_request
    def _apply_response_format(response: Response) -> Response:
        config = current_app.config.get("RESPONSE_FORMAT_CONFIG")
        if not config:
            return response

        endpoint = request.endpoint
        if endpoint is None:
            return response

        forced = config["forced_endpoints"]
        base: Set[str] = config["base_endpoints"]

        if endpoint in forced:
            target_format = forced[endpoint]
        elif endpoint in base:
            target_format = getattr(g, "response_format", "html")
        else:
            return response

        return _convert_response(response, target_format)

    app.config["RESPONSE_FORMAT_HANDLERS_REGISTERED"] = True


@dataclass(slots=True)
class _RuleDetails:
    """Capture the relevant attributes from a Werkzeug routing rule."""

    rule: str
    methods: Optional[list[str]] = None
    defaults: Optional[Dict[str, Any]] = None
    subdomain: Optional[str] = None
    strict_slashes: Optional[bool] = None
    provide_automatic_options: Optional[bool] = None

    @classmethod
    def from_rule(
        cls, rule: Any
    ) -> "_RuleDetails":  # pragma: no cover - exercised indirectly
        methods = None
        if getattr(rule, "methods", None):
            methods = [m for m in rule.methods if m not in {"HEAD", "OPTIONS"}]
        return cls(
            rule=str(rule),
            methods=methods,
            defaults=getattr(rule, "defaults", None),
            subdomain=getattr(rule, "subdomain", None),
            strict_slashes=getattr(rule, "strict_slashes", None),
            provide_automatic_options=getattr(rule, "provide_automatic_options", True),
        )


def _rule_exists(app: Flask, candidate: str) -> bool:
    for existing in app.url_map.iter_rules():
        if str(existing) == candidate:
            return True
    return False


def resolve_format_from_accept(accept: MIMEAccept, default_format: str = "html") -> str:
    """Determine the preferred response format from the Accept header."""

    best_quality = -1.0
    best_format = default_format

    for mimetype, fmt in ACCEPT_ALIASES.items():
        quality = accept[mimetype]
        if quality is None or quality <= 0:
            continue
        if quality > best_quality or (
            quality == best_quality and _prefer(fmt, best_format)
        ):
            best_quality = quality
            best_format = fmt

    if best_quality >= 0:
        return best_format

    # Fallback to wildcards if explicit matches were not provided.
    wildcard_preferences = (
        ("application/*", "json"),
        ("text/*", "html"),
        ("*/*", "html"),
    )

    for mimetype, fmt in wildcard_preferences:
        quality = accept[mimetype]
        if quality and quality > 0:
            return fmt

    return default_format


def _prefer(candidate: str, current: str) -> bool:
    priority = ["json", "csv", "html", "txt", "md", "xml"]
    return priority.index(candidate) < priority.index(current)


def _convert_response(response: Response, target_format: str) -> Response:
    if target_format not in SUPPORTED_FORMATS:
        return response

    desired_mimetype = SUPPORTED_FORMATS[target_format]

    if 300 <= response.status_code < 400:
        response.mimetype = desired_mimetype
        return response

    if (response.mimetype or "").split(";")[0] == desired_mimetype:
        return response

    original_mimetype = response.mimetype or "text/html"

    payload: Any
    source_format = "text"
    if response.is_json:
        payload = response.get_json()
        source_format = "json"
    else:
        payload = response.get_data(as_text=True)

    converters = {
        "html": _convert_to_html,
        "json": _convert_to_json,
        "txt": _convert_to_text,
        "md": _convert_to_markdown,
        "xml": _convert_to_xml,
        "csv": _convert_to_csv,
    }

    converter = converters.get(target_format)
    if converter is None:
        return response

    body = converter(payload, source_format, original_mimetype)
    response.set_data(body)
    response.mimetype = desired_mimetype
    response.charset = "utf-8"
    return response


def _convert_to_html(payload: Any, source_format: str, _original: str) -> str:
    if source_format == "json":
        formatted = json.dumps(payload, indent=2, sort_keys=True)
        return f"<pre>{html_escape(formatted)}</pre>"
    return str(payload)


def _convert_to_json(payload: Any, source_format: str, original: str) -> str:
    if source_format == "json":
        return json.dumps(payload)
    content = str(payload)
    envelope = {"content": content, "content_type": original}
    return json.dumps(envelope)


def _convert_to_text(payload: Any, source_format: str, _original: str) -> str:
    if source_format == "json":
        return _json_to_text(payload)
    return _strip_html(str(payload))


def _convert_to_markdown(payload: Any, source_format: str, _original: str) -> str:
    if source_format == "json":
        return _json_to_markdown(payload)
    return _strip_html(str(payload))


def _convert_to_xml(payload: Any, source_format: str, original: str) -> str:
    if source_format == "json":
        return _value_to_xml(payload, "response")
    content = html_escape(_sanitize_xml_text(str(payload)))
    content_type = html_escape(original)
    return f"<response><content_type>{content_type}</content_type><content>{content}</content></response>"


def _strip_html(text: str) -> str:
    stripped = _HTML_TAG_RE.sub("", text)
    return html_unescape(stripped)


def _convert_to_csv(payload: Any, source_format: str, original: str) -> str:
    if source_format == "json":
        return _json_to_csv(payload)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["content_type", "content"])
    writer.writerow([original, _strip_html(str(payload))])
    return buffer.getvalue()


def _json_to_csv(payload: Any) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if isinstance(payload, Mapping):
        _write_csv_row(
            writer, payload.keys(), [payload.get(key) for key in payload.keys()]
        )
        return buffer.getvalue()

    if isinstance(payload, Sequence) and not isinstance(
        payload, (str, bytes, bytearray)
    ):
        rows = list(payload)
        if not rows:
            return ""

        if all(isinstance(item, Mapping) for item in rows):
            header: list[str] = []
            for item in rows:
                for key in item.keys():
                    if key not in header:
                        header.append(str(key))

            writer.writerow(header)
            for item in rows:
                writer.writerow(
                    [_stringify_csv_value(item.get(column)) for column in header]
                )
            return buffer.getvalue()

        writer.writerow(["value"])
        for item in rows:
            writer.writerow([_stringify_csv_value(item)])
        return buffer.getvalue()

    writer.writerow(["value"])
    writer.writerow([_stringify_csv_value(payload)])
    return buffer.getvalue()


def _json_to_text(payload: Any) -> str:
    if isinstance(payload, Mapping):
        return "\n".join(
            f"{key}: {_stringify_csv_value(value)}" for key, value in payload.items()
        )

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        named_values = _extract_named_values(payload)
        if named_values:
            return "\n".join(named_values)
        return "\n".join(_stringify_csv_value(item) for item in payload)

    return json.dumps(payload, indent=2, sort_keys=True)


def _json_to_markdown(payload: Any) -> str:
    if isinstance(payload, Mapping):
        return "\n".join(
            f"- **{key}**: {_stringify_csv_value(value)}"
            for key, value in payload.items()
        )

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        named_values = _extract_named_values(payload)
        if named_values:
            return "\n".join(f"- {value}" for value in named_values)
        return "\n".join(f"- {_stringify_csv_value(item)}" for item in payload)

    formatted = json.dumps(payload, indent=2, sort_keys=True)
    return f"```json\n{formatted}\n```"


def _extract_named_values(payload: Sequence[Any]) -> list[str] | None:
    names: list[str] = []
    for item in payload:
        if not isinstance(item, Mapping):
            return None
        name_value = item.get("name")
        if name_value is None:
            return None
        names.append(str(name_value))
    return names


def _write_csv_row(
    writer: csv.writer, header: Iterable[str], values: Iterable[Any]
) -> None:
    header_list = [str(column) for column in header]
    writer.writerow(header_list)
    writer.writerow([_stringify_csv_value(value) for value in values])


def _stringify_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set, Mapping)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _value_to_xml(value: Any, tag: str) -> str:
    if isinstance(value, dict):
        parts = [f"<{tag}>"]
        for key, item in value.items():
            parts.append(_value_to_xml(item, _sanitize_xml_tag(str(key))))
        parts.append(f"</{tag}>")
        return "".join(parts)
    if isinstance(value, (list, tuple)):
        parts = [f"<{tag}>"]
        for item in value:
            parts.append(_value_to_xml(item, "item"))
        parts.append(f"</{tag}>")
        return "".join(parts)
    if value is None:
        return f"<{tag} />"
    sanitized = _sanitize_xml_text(str(value))
    return f"<{tag}>{html_escape(sanitized)}</{tag}>"


def _sanitize_xml_tag(candidate: str) -> str:
    sanitized = _XML_TAG_RE.sub("_", candidate.strip())
    if not sanitized:
        return "item"
    if sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    return sanitized


def _sanitize_xml_text(value: str) -> str:
    """Replace control characters that are not permitted in XML documents."""

    return _XML_INVALID_CHAR_RE.sub(
        lambda match: f"\\x{ord(match.group(0)):02x}", value
    )


def render_payload(payload: Any, target_format: str) -> tuple[str, str]:
    """Render a structured payload into the requested format."""

    format_key = target_format if target_format in SUPPORTED_FORMATS else "json"
    converters: Mapping[str, Any] = {
        "html": lambda value: _convert_to_html(
            value, "json", "application/json"
        ),
        "json": lambda value: json.dumps(value, ensure_ascii=False),
        "txt": _json_to_text,
        "md": _json_to_markdown,
        "xml": lambda value: _value_to_xml(value, "response"),
        "csv": _json_to_csv,
    }

    converter = converters.get(format_key, converters["json"])
    body = converter(payload)
    mimetype = SUPPORTED_FORMATS.get(format_key, "application/json")
    return body, mimetype


__all__ = [
    "register_response_format_handlers",
    "resolve_format_from_accept",
    "render_payload",
]
