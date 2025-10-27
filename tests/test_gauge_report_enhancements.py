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
  <p>Screenshot path: /__w/Viewer/Viewer/gauge/reports/html-report/secureapp-artifacts/example.png</p>
  <p>Metadata path: /__w/Viewer/Viewer/gauge/reports/html-report/secureapp-artifacts/example.json</p>
</body></html>
""",
        encoding="utf-8",
    )

    detail_html = gauge_dir / "detail.html"
    detail_html.write_text(
        "See /__w/Viewer/Viewer/gauge/reports/html-report/secureapp-artifacts/example.png and /__w/Viewer/Viewer/gauge/reports/html-report/secureapp-artifacts/example.json for more details.",
        encoding="utf-8",
    )

    public_base_url = "https://example.test/reports/gauge-specs"
    updated = enhance_gauge_report(gauge_dir, public_base_url=public_base_url)
    assert updated is True

    updated_index = index_html.read_text(encoding="utf-8")
    png_href = "https://example.test/reports/gauge-specs/secureapp-artifacts/example.png"
    json_href = "https://example.test/reports/gauge-specs/secureapp-artifacts/example.json"
    assert f'<img src="{png_href}"' in updated_index
    assert f'href="{png_href}"' in updated_index
    assert 'class="secureapp-inline-snapshot"' in updated_index
    assert '<a class="secureapp-inline-metadata"' in updated_index
    assert '>info<' in updated_index
    assert '/__w/' not in updated_index

    updated_detail = detail_html.read_text(encoding="utf-8")
    assert f'<img src="{png_href}"' in updated_detail
    assert f'href="{json_href}"' in updated_detail
    assert '>info<' in updated_detail
    assert '/__w/' not in updated_detail

    assert '<section class="gauge-screenshot-gallery">' in updated_index
    assert f'href="{json_href}"' in updated_index
