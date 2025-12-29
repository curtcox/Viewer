"""HTML rendering utilities for meta route."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import current_app
from markupsafe import Markup, escape

from cid_presenter import format_cid, render_cid_link


def render_scalar_html(value: Any) -> Markup:
    """Return HTML for a scalar metadata value."""
    if isinstance(value, str):
        trimmed = value.strip()
        if (
            trimmed.startswith("/")
            or trimmed.startswith("http://")
            or trimmed.startswith("https://")
        ):
            escaped_trimmed = escape(trimmed)
            return Markup(
                f'<a href="{escaped_trimmed}"><code>{escaped_trimmed}</code></a>'
            )
        return Markup(f"<code>{escape(value)}</code>")

    if value is None:
        return Markup("<code>null</code>")

    if isinstance(value, bool):
        return Markup(f"<code>{str(value).lower()}</code>")

    if isinstance(value, (int, float)):
        return Markup(f"<code>{value}</code>")

    return Markup(f"<code>{escape(str(value))}</code>")


def render_cid_popup_pair(value: Any) -> Markup:
    """Return markup showing a CID link with a companion meta popup link."""

    cid_value = format_cid(value)
    if not cid_value:
        return Markup("")

    cid_link = render_cid_link(cid_value)
    meta_href = f"/meta/{cid_value}"
    popup_link = Markup(
        '<a class="cid-meta-popup" href="{href}" title="View CID metadata">'
        '<i class="fas fa-circle-info"></i>'
        "</a>"
    ).format(href=escape(meta_href))

    return Markup(
        '<span class="cid-link-popup d-inline-flex align-items-center gap-2">{cid_link}'
        '<span class="cid-meta-popup-link">{popup}</span>'
        "</span>"
    ).format(cid_link=cid_link, popup=popup_link)


def render_related_cids_html(value: Dict[str, Any]) -> Markup:
    """Return HTML for related CID mappings using the standard CID/popup pair."""

    items: List[Markup] = []
    for key, cid_value in value.items():
        items.append(
            Markup('<li><span class="meta-key">{}</span>: {}</li>').format(
                escape(key), render_cid_popup_pair(cid_value)
            )
        )

    return Markup('<ul class="meta-dict meta-related-cids">{}</ul>').format(
        Markup("".join(items))
    )


def render_value_html(value: Any, *, parent_key: Optional[str] = None) -> Markup:
    """Recursively render metadata as HTML."""
    if isinstance(value, dict):
        if parent_key == "related_cids":
            return render_related_cids_html(value)

        items = []
        for key, child in value.items():
            items.append(
                Markup('<li><span class="meta-key">{}</span>: {}</li>').format(
                    escape(key), render_value_html(child, parent_key=key)
                )
            )
        return Markup('<ul class="meta-dict">{}</ul>').format(Markup("".join(items)))

    if isinstance(value, (list, tuple, set)):
        items = [
            Markup("<li>{}</li>").format(
                render_value_html(child, parent_key=parent_key)
            )
            for child in value
        ]
        return Markup('<ol class="meta-list">{}</ol>').format(Markup("".join(items)))

    return render_scalar_html(value)


@lru_cache()
def load_page_test_cross_reference(app_root: str) -> Dict[str, Dict[str, List[str]]]:
    """Return a mapping of templates to their documented automated checks."""

    doc_path = Path(app_root) / "docs" / "page_test_cross_reference.md"
    if not doc_path.is_file():
        return {}

    sections = {
        "routes": "routes",
        "unit tests": "unit_tests",
        "integration tests": "integration_tests",
        "specs": "specs",
    }

    mapping: Dict[str, Dict[str, List[str]]] = {}
    current_template: Optional[str] = None
    current_section: Optional[str] = None

    with doc_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("## "):
                template_name = line[3:].strip()
                current_template = template_name
                mapping[current_template] = {key: [] for key in sections.values()}
                current_section = None
                continue

            if line.startswith("**") and line.endswith("**"):
                header_text = line[2:-2].strip()
                if header_text.endswith(":"):
                    header_text = header_text[:-1]
                current_section = sections.get(header_text.lower())
                continue

            if not line.startswith("- ") or not current_template or not current_section:
                continue

            value = line[2:].strip()
            if value == "_None_":
                continue

            if value.startswith("`") and value.endswith("`"):
                value = value[1:-1]

            mapping[current_template][current_section].append(value)

    return mapping


def templates_for_metadata(metadata: Dict[str, Any]) -> List[str]:
    """Return templates referenced by the supplied metadata in declaration order."""

    templates: List[str] = []
    for link in metadata.get("source_links", []) or []:
        if not isinstance(link, str):
            continue
        if not link.startswith("/source/"):
            continue
        relative = link[len("/source/") :]
        if not relative.startswith("templates/"):
            continue
        if relative not in templates:
            templates.append(relative)

    return templates


def reference_to_source_link(reference: str, category: str) -> Optional[str]:
    """Return a /source URL for the supplied reference if available."""

    if category in {"unit_tests", "integration_tests"}:
        file_part = reference.split("::", 1)[0]
        if file_part.endswith(".py"):
            return f"/source/{file_part}"
        return None

    if category == "specs":
        file_part = reference.split(" — ", 1)[0].strip()
        if file_part and not file_part.startswith("specs/"):
            file_part = f"specs/{file_part}"
        if file_part:
            return f"/source/{file_part}"

    return None


def render_reference_item(reference: str, category: str) -> Markup:
    """Return HTML for a single documented automated check."""

    href = reference_to_source_link(reference, category)
    if category == "specs" and " — " in reference:
        name, description = reference.split(" — ", 1)
        link_html = Markup(f"<code>{escape(name)}</code>")
        if href:
            link_html = Markup(f'<a href="{escape(href)}">{link_html}</a>')
        return Markup(f"{link_html} — {escape(description)}")

    content = Markup(f"<code>{escape(reference)}</code>")
    if href:
        return Markup(f'<a href="{escape(href)}">{content}</a>')
    return content


def render_related_tests_section(metadata: Dict[str, Any]) -> str:
    """Return an HTML section linking to tests that exercise the page."""

    templates = templates_for_metadata(metadata)
    if not templates:
        return ""

    cross_reference = load_page_test_cross_reference(current_app.root_path)
    categories = [
        ("unit_tests", "Unit tests"),
        ("integration_tests", "Integration tests"),
        ("specs", "Specs"),
    ]

    aggregated: Dict[str, List[str]] = {key: [] for key, _ in categories}
    for template in templates:
        data = cross_reference.get(template)
        if not data:
            continue
        for key, _ in categories:
            aggregated[key].extend(data.get(key, []))

    if not any(aggregated[key] for key, _ in categories):
        return ""

    for key in aggregated:
        aggregated[key] = list(dict.fromkeys(aggregated[key]))

    template_links = [
        Markup('<li><a href="{href}"><code>{label}</code></a></li>').format(
            href=escape(f"/source/{template}"), label=escape(template)
        )
        for template in templates
    ]

    sections_html: List[str] = [
        '<section class="meta-related-tests">',
        "<h2>Related automated coverage</h2>",
        "<p>Tests below are sourced from <code>docs/page_test_cross_reference.md</code> for templates rendered by this page.</p>",
        "<h3>Templates</h3>",
        '<ul class="meta-related-tests-templates">',
        "".join(str(item) for item in template_links),
        "</ul>",
    ]

    for key, label in categories:
        sections_html.append(f"<h3>{escape(label)}</h3>")
        items = aggregated[key]
        if items:
            sections_html.append('<ul class="meta-related-tests-list">')
            for reference in items:
                rendered = render_reference_item(reference, key)
                sections_html.append(f"<li>{rendered}</li>")
            sections_html.append("</ul>")
        else:
            sections_html.append("<p><em>None documented.</em></p>")

    sections_html.append("</section>")
    return "".join(sections_html)


def render_metadata_html(metadata: Dict[str, Any]) -> str:
    """Return an HTML page for the supplied metadata."""
    body = render_value_html(metadata)
    related_tests = render_related_tests_section(metadata)
    styles = """
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 1rem; }
    ul.meta-dict, ol.meta-list { list-style: none; padding-left: 1.25rem; }
    ul.meta-dict > li { margin-bottom: 0.5rem; }
    ul.meta-dict ul.meta-dict, ul.meta-dict ol.meta-list { margin-top: 0.5rem; }
    .meta-key { font-weight: 600; }
    code { background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 0.25rem; }
    a code { color: inherit; }
    .meta-related-tests { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; }
    .meta-related-tests h2 { margin-bottom: 0.5rem; }
    .meta-related-tests h3 { margin-top: 1.25rem; margin-bottom: 0.5rem; }
    .meta-related-tests ul { list-style: disc; padding-left: 1.5rem; }
    .meta-related-tests-templates { list-style: none; padding-left: 0; display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
    .meta-related-tests-templates li { list-style: none; }
    """
    return f"""<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Meta Inspector</title><style>{styles}</style></head><body><h1>Meta inspector</h1>{body}{related_tests}</body></html>"""
