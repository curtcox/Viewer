"""Tests for Gauge artifact helpers."""

from __future__ import annotations

import json
import sys
import types

import importlib.util
from pathlib import Path


class _FakeResponse:
    def __init__(self, *, body: bytes, mimetype: str, status: int = 200) -> None:
        self._body = body
        self.mimetype = mimetype
        self.status_code = status
        self.request = types.SimpleNamespace(method="GET", path="/example")

    def get_data(self, as_text: bool = False):  # type: ignore[override]
        if as_text:
            return self._body.decode("utf-8")
        return self._body


def _load_artifacts_module():
    module_name = "test_step_impl_artifacts"
    module_path = Path(__file__).resolve().parents[1] / "step_impl" / "artifacts.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load artifacts module for testing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


artifacts = _load_artifacts_module()


class _FakePage:  # pylint: disable=attribute-defined-outside-init
    """Mock page object that captures method calls as attributes for testing."""
    def __init__(self, *, allow_wait_until: bool = True) -> None:
        self._allow_wait_until = allow_wait_until

    async def setViewport(self, viewport: dict[str, int]) -> None:  # noqa: N802 - match pyppeteer API
        self.viewport = viewport

    async def setContent(self, html_document: str, waitUntil: str | None = None) -> None:  # noqa: N802 - match pyppeteer API
        if not self._allow_wait_until and waitUntil is not None:
            raise TypeError("unexpected keyword argument 'waitUntil'")
        self.html_document = html_document
        self.wait_until = waitUntil

    async def waitForFunction(self, expression: str) -> None:  # noqa: N802 - match pyppeteer API
        self.wait_for_function = expression

    async def screenshot(self, *, fullPage: bool) -> bytes:  # noqa: N803 - match pyppeteer API
        self.full_page = fullPage
        return b"fake screenshot"


class _FakeBrowser:
    def __init__(self, captured: dict[str, object], *, page: _FakePage | None = None) -> None:
        self._captured = captured
        self._page = page or _FakePage()

    async def newPage(self) -> _FakePage:  # noqa: N802 - match pyppeteer API
        self._captured["page"] = self._page
        return self._page

    async def close(self) -> None:
        self._captured["closed"] = True


def test_render_browser_screenshot_disables_signal_handlers(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_launch(*, args: list[str], **kwargs: object) -> _FakeBrowser:
        captured.update(kwargs)
        captured["args"] = args
        return _FakeBrowser(captured)

    fake_module = types.ModuleType("pyppeteer")
    fake_module.launch = _fake_launch
    monkeypatch.setitem(sys.modules, "pyppeteer", fake_module)

    result, error = artifacts._render_browser_screenshot("<html></html>")

    assert result == b"fake screenshot"
    assert error is None
    assert captured["handleSIGINT"] is False
    assert captured["handleSIGTERM"] is False
    assert captured["handleSIGHUP"] is False
    assert captured["args"] == [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]
    assert captured["closed"] is True

    page = captured["page"]
    assert isinstance(page, _FakePage)
    assert page.viewport == {"width": artifacts._IMAGE_WIDTH, "height": 720}
    assert page.html_document == "<html></html>"
    assert page.wait_until == "networkidle0"
    assert page.full_page is True


def test_render_browser_screenshot_supports_legacy_setcontent(monkeypatch) -> None:
    captured: dict[str, object] = {}
    page = _FakePage(allow_wait_until=False)

    async def _fake_launch(*, args: list[str], **kwargs: object) -> _FakeBrowser:
        captured.update(kwargs)
        captured["args"] = args
        return _FakeBrowser(captured, page=page)

    fake_module = types.ModuleType("pyppeteer")
    fake_module.launch = _fake_launch
    monkeypatch.setitem(sys.modules, "pyppeteer", fake_module)

    result, error = artifacts._render_browser_screenshot("<html></html>")

    assert result == b"fake screenshot"
    assert error is None
    assert page.html_document == "<html></html>"
    assert page.wait_until is None
    assert page.wait_for_function == "document.readyState === 'complete'"


def test_render_browser_screenshot_falls_back_when_launch_fails(monkeypatch) -> None:
    async def _fake_launch(**_: object) -> _FakeBrowser:
        raise RuntimeError("chromium download failed")

    fake_module = types.ModuleType("pyppeteer")
    fake_module.launch = _fake_launch
    monkeypatch.setitem(sys.modules, "pyppeteer", fake_module)

    result, error = artifacts._render_browser_screenshot("<html></html>")

    assert result is None
    assert error is not None
    assert "chromium download failed" in error


def test_attach_response_snapshot_generates_text_preview_for_non_html(tmp_path, monkeypatch) -> None:
    response = _FakeResponse(body=b"{\"ok\": true}", mimetype="application/json")

    attachments: list[tuple[str, str]] = []

    class _StubMessages:
        @staticmethod
        def attach_binary(data: bytes, mime_type: str, name: str) -> None:  # noqa: D401 - match Gauge API
            attachments.append((mime_type, name))

        @staticmethod
        def write_message(message: str) -> None:
            attachments.append(("message", message))

    monkeypatch.setenv("GAUGE_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(artifacts, "Messages", _StubMessages)

    artifacts.attach_response_snapshot(response, label="API response")

    png_files = sorted(tmp_path.glob("*.png"))
    json_files = sorted(tmp_path.glob("*.json"))

    assert len(png_files) == 1
    assert len(json_files) == 1
    assert ("image/png", png_files[0].name) in attachments
    assert ("application/json", json_files[0].name) in attachments

    metadata = json.loads(json_files[0].read_text(encoding="utf-8"))
    screenshot = metadata["screenshot"]

    assert screenshot["captured"] is True
    assert screenshot["placeholder"] is False
    assert screenshot["generated"] == "text-preview"
    assert screenshot["details"] == [
        "Response body is not HTML; browser screenshot skipped."
    ]
