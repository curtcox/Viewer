"""Ensure the source browser can stream Gauge spec reports."""
from __future__ import annotations

import shutil
from pathlib import Path

from app import create_app
from routes import source as source_module


def test_source_serves_gauge_report():
    app = create_app({"TESTING": True})
    client = app.test_client()

    reports_root = Path(app.root_path) / "reports" / "html-report"
    reports_root.mkdir(parents=True, exist_ok=True)
    report_file = reports_root / "index.html"
    report_file.write_text("<html><body>Gauge spec report</body></html>", encoding="utf-8")

    try:
        source_module._get_tracked_paths.cache_clear()
        source_module._get_all_project_files.cache_clear()
        response = client.get("/source/reports/html-report/index.html")
        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert b"Gauge spec report" in response.data
    finally:
        if report_file.exists():
            report_file.unlink()
        if reports_root.parent.exists():
            shutil.rmtree(reports_root.parent)
