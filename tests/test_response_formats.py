"""Unit tests for response format negotiation utilities."""
from __future__ import annotations

from werkzeug.datastructures import MIMEAccept

from response_formats import resolve_format_from_accept


def test_resolve_format_prefers_highest_quality_html() -> None:
    accept = MIMEAccept([("application/json", 0.5), ("text/html", 0.9)])
    assert resolve_format_from_accept(accept) == "html"


def test_resolve_format_prefers_json_when_higher_quality() -> None:
    accept = MIMEAccept([("application/json", 0.9), ("text/html", 0.6)])
    assert resolve_format_from_accept(accept) == "json"


def test_resolve_format_handles_xml_only_accept_header() -> None:
    accept = MIMEAccept([("application/xml", 0.8)])
    assert resolve_format_from_accept(accept) == "xml"


def test_resolve_format_falls_back_to_wildcard_application() -> None:
    accept = MIMEAccept([("application/*", 0.5)])
    assert resolve_format_from_accept(accept) == "json"


def test_resolve_format_defaults_to_html_when_header_missing() -> None:
    accept = MIMEAccept([])
    assert resolve_format_from_accept(accept) == "html"
