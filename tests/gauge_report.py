"""Utilities for enhancing Gauge HTML reports with captured artifacts."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from textwrap import dedent
from typing import Iterable, Sequence

_STYLE_START = "<!-- secureapp-gauge-gallery-style:start -->"
_STYLE_END = "<!-- secureapp-gauge-gallery-style:end -->"
_GALLERY_START = "<!-- secureapp-gauge-gallery:start -->"
_GALLERY_END = "<!-- secureapp-gauge-gallery:end -->"


def enhance_gauge_report(gauge_base: Path, *, artifacts_subdir: str = "secureapp-artifacts") -> bool:
    """Inject a screenshot gallery into the Gauge report if artifacts exist.

    Parameters
    ----------
    gauge_base:
        Path to the directory that contains ``index.html`` for the Gauge report.
    artifacts_subdir:
        Name of the directory underneath ``gauge_base`` that contains the
        captured PNG and JSON artifacts.

    Returns
    -------
    bool
        ``True`` if the report was updated, otherwise ``False``.
    """

    gauge_base = gauge_base.resolve()
    index_path = gauge_base / "index.html"
    artifacts_dir = gauge_base / artifacts_subdir

    if not index_path.exists() or not artifacts_dir.exists():
        return False

    png_files = sorted(artifacts_dir.glob("*.png"))
    if not png_files:
        return False

    gallery_items = list(_build_gallery_items(png_files, gauge_base))
    if not gallery_items:
        return False

    index_html = index_path.read_text(encoding="utf-8")
    index_html = _strip_marked_block(index_html, _STYLE_START, _STYLE_END)
    index_html = _strip_marked_block(index_html, _GALLERY_START, _GALLERY_END)

    style_block = dedent(
        """
        {start}
        <style>
        .gauge-screenshot-gallery {{ margin-top: 2rem; }}
        .gauge-screenshot-gallery h2 {{ font-size: 1.5rem; margin-bottom: 1rem; }}
        .gauge-screenshot-gallery .gallery-grid {{ display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
        .gauge-screenshot-gallery figure {{ margin: 0; }}
        .gauge-screenshot-gallery img {{ width: 100%; height: auto; border: 1px solid #d0d7de; border-radius: 6px; box-shadow: 0 1px 3px rgba(27, 31, 36, 0.12); }}
        .gauge-screenshot-gallery figcaption {{ margin-top: 0.5rem; font-size: 0.95rem; }}
        .gauge-screenshot-gallery a {{ color: #0366d6; text-decoration: none; }}
        .gauge-screenshot-gallery a:hover {{ text-decoration: underline; }}
        </style>
        {end}
        """
    ).format(start=_STYLE_START, end=_STYLE_END)

    gallery_block = dedent(
        """
        {start}
        <section class="gauge-screenshot-gallery">
          <h2>Captured page screenshots</h2>
          <div class="gallery-grid">
        {items}
          </div>
        </section>
        {end}
        """
    ).format(
        start=_GALLERY_START,
        end=_GALLERY_END,
        items="\n".join(f"            {item}" for item in gallery_items),
    )

    if "</head>" in index_html:
        index_html = index_html.replace("</head>", style_block + "</head>")
    else:
        index_html = style_block + index_html

    if "</body>" in index_html:
        index_html = index_html.replace("</body>", gallery_block + "</body>")
    else:
        index_html += gallery_block

    index_path.write_text(index_html, encoding="utf-8")
    return True


def _build_gallery_items(png_files: Iterable[Path], gauge_base: Path) -> Iterable[str]:
    for png_path in png_files:
        stem = png_path.stem
        json_path = png_path.with_suffix(".json")
        label = stem

        if json_path.exists():
            try:
                metadata = json.loads(json_path.read_text(encoding="utf-8"))
                label = str(metadata.get("label", label))
            except json.JSONDecodeError:
                label = stem

        rel_png = png_path.relative_to(gauge_base).as_posix()
        rel_json = json_path.relative_to(gauge_base).as_posix() if json_path.exists() else None

        caption = escape(label)
        json_link = ""
        if rel_json:
            json_link = f' (<a href="{rel_json}">request/response</a>)'

        item_html = (
            "<figure class=\"gauge-screenshot\">"
            f'<a href="{rel_png}" target="_blank" rel="noopener">'
            f'<img src="{rel_png}" alt="{caption}" loading="lazy" />'
            "</a>"
            f"<figcaption>{caption}{json_link}</figcaption>"
            "</figure>"
        )
        yield item_html


def _strip_marked_block(html: str, start_marker: str, end_marker: str) -> str:
    start = html.find(start_marker)
    while start != -1:
        end = html.find(end_marker, start)
        if end == -1:
            break
        end += len(end_marker)
        # Remove any trailing newline to avoid accumulating blank lines.
        slice_end = end
        while slice_end < len(html) and html[slice_end] in "\r\n":
            slice_end += 1
        html = html[:start].rstrip("\r\n") + html[slice_end:]
        start = html.find(start_marker)
    return html


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enhance Gauge HTML reports with screenshots.")
    parser.add_argument("gauge_base", type=Path, help="Directory containing the Gauge index.html file.")
    parser.add_argument(
        "--artifacts-subdir",
        default="secureapp-artifacts",
        help="Relative path containing PNG and JSON artifacts.",
    )
    parsed = parser.parse_args(argv)

    enhance_gauge_report(parsed.gauge_base, artifacts_subdir=parsed.artifacts_subdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
