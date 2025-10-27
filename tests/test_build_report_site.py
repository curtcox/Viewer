import importlib.util
import json
import sys
from pathlib import Path


def _load_build_report_module():
    module_name = "test_build_report_site"
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "build-report-site.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load build-report-site module for testing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


build_report = _load_build_report_module()


def test_collect_screenshot_issues_counts_placeholders(tmp_path) -> None:
    gauge_dir = tmp_path / "gauge"
    artifacts_dir = gauge_dir / "secureapp-artifacts"
    artifacts_dir.mkdir(parents=True)

    (artifacts_dir / "one.json").write_text(
        json.dumps(
            {
                "screenshot": {
                    "captured": False,
                    "placeholder": True,
                    "details": [
                        "pyppeteer is not installed.",
                        "Unable to read the shared placeholder image.",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    (artifacts_dir / "two.json").write_text(
        json.dumps(
            {
                "screenshot": {
                    "captured": True,
                    "placeholder": False,
                    "details": "Response body is not HTML; browser screenshot skipped.",
                    "generated": "text-preview",
                }
            }
        ),
        encoding="utf-8",
    )

    # Captured screenshot should not be counted.
    (artifacts_dir / "three.json").write_text(
        json.dumps(
            {
                "screenshot": {
                    "captured": True,
                    "placeholder": False,
                }
            }
        ),
        encoding="utf-8",
    )

    count, reasons = build_report._collect_screenshot_issues(gauge_dir)

    assert count == 1
    assert reasons == [
        "pyppeteer is not installed.",
        "Unable to read the shared placeholder image.",
    ]


def test_format_screenshot_notice_builds_section() -> None:
    notice = build_report._format_screenshot_notice(
        2, ["First reason", "Second reason"]
    )

    assert notice is not None
    assert "Gauge screenshot status" in notice
    assert "<li>First reason</li>" in notice
    assert "<li>Second reason</li>" in notice


def test_write_landing_page_includes_notice(tmp_path) -> None:
    notice = "<section class=\"screenshot-status\">Example</section>"
    build_report._write_landing_page(tmp_path, screenshot_notice=notice)

    index_path = tmp_path / "index.html"
    content = index_path.read_text(encoding="utf-8")

    assert notice in content
