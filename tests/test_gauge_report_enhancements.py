from __future__ import annotations

import json
from pathlib import Path

from tests.gauge_report import enhance_gauge_report


def _write_png(path: Path) -> None:
    # Minimal PNG header with IHDR and IEND chunks.
    path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108020000009077053E0000000A49444154789C6360000002000100FFFF03000006000557BF280000000049454E44AE426082"
        )
    )


def test_enhance_gauge_report_converts_artifact_paths(tmp_path):
    gauge_dir = tmp_path / "gauge"
    artifacts_dir = gauge_dir / "secureapp-artifacts"
    artifacts_dir.mkdir(parents=True)

    png_path = artifacts_dir / "example.png"
    _write_png(png_path)
    metadata = {"label": "GET /demo"}
    png_path.with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")

    index_html = gauge_dir / "index.html"
    index_html.write_text(
        """<!DOCTYPE html>
<html><head><title>Gauge</title></head>
<body>
  <p>Screenshot path: secureapp-artifacts/example.png</p>
  <p>Metadata path: secureapp-artifacts/example.json</p>
</body></html>
""",
        encoding="utf-8",
    )

    detail_html = gauge_dir / "detail.html"
    detail_html.write_text(
        "See secureapp-artifacts/example.png and secureapp-artifacts/example.json for more details.",
        encoding="utf-8",
    )

    updated = enhance_gauge_report(gauge_dir)
    assert updated is True

    updated_index = index_html.read_text(encoding="utf-8")
    assert '<img src="secureapp-artifacts/example.png"' in updated_index
    assert 'class="secureapp-inline-snapshot"' in updated_index
    assert 'Metadata for GET /demo' in updated_index or 'JSON metadata' in updated_index
    assert '<a class="secureapp-inline-metadata"' in updated_index

    updated_detail = detail_html.read_text(encoding="utf-8")
    assert '<img src="secureapp-artifacts/example.png"' in updated_detail
    assert '<a class="secureapp-inline-metadata"' in updated_detail

    assert '<section class="gauge-screenshot-gallery">' in updated_index
