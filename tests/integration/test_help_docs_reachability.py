"""Integration tests to ensure docs are reachable starting from /help."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def _extract_hrefs(html: str) -> set[str]:
    hrefs: set[str] = set()
    start = 0
    while True:
        idx = html.find("href=", start)
        if idx == -1:
            return hrefs
        quote_idx = idx + 5
        if quote_idx >= len(html):
            return hrefs
        quote_char = html[quote_idx]
        if quote_char not in ('"', "'"):
            start = quote_idx
            continue
        end_idx = html.find(quote_char, quote_idx + 1)
        if end_idx == -1:
            return hrefs
        href = html[quote_idx + 1 : end_idx].strip()
        if href:
            hrefs.add(href)
        start = end_idx + 1


def test_all_docs_files_are_linked_and_reachable_from_help(client):
    response = client.get("/help")
    assert response.status_code == 200

    help_html = response.get_data(as_text=True)
    hrefs = _extract_hrefs(help_html)

    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    docs_files = sorted(
        entry.name
        for entry in docs_dir.iterdir()
        if entry.is_file() and not entry.name.startswith(".")
    )

    expected_paths: list[str] = [f"/source/docs/{name}" for name in docs_files]

    for expected in expected_paths:
        assert expected in hrefs

        linked = urlparse(expected)
        linked_path = linked.path
        linked_response = client.get(linked_path)
        assert linked_response.status_code == 200
