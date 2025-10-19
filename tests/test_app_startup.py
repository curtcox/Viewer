"""Tests that ensure the Flask application can start successfully."""

from __future__ import annotations

from pathlib import Path

import pytest

import app as app_module
from logfire.exceptions import LogfireConfigError


@pytest.fixture
def app_config_factory(tmp_path: Path):
    """Return a helper that produces isolated database configurations."""

    def _make_config(name: str) -> dict[str, object]:
        db_path = tmp_path / f"startup-{name}.sqlite"
        return {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
        }

    return _make_config


def test_create_app_serves_homepage(monkeypatch: pytest.MonkeyPatch, app_config_factory):
    """The factory should create an app whose homepage can be rendered."""

    monkeypatch.delenv("LOGFIRE_SEND_TO_LOGFIRE", raising=False)

    app_instance = app_module.create_app(app_config_factory("basic"))
    client = app_instance.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Viewer" in response.get_data(as_text=True)

    with app_instance.app_context():
        status = app_instance.config["OBSERVABILITY_STATUS"]
        assert status["logfire_available"] is False
        assert status["logfire_reason"] == "LOGFIRE_SEND_TO_LOGFIRE not set"


def test_create_app_handles_logfire_configuration_errors(
    monkeypatch: pytest.MonkeyPatch, app_config_factory
):
    """Logfire misconfiguration should not stop the application from starting."""

    monkeypatch.setenv("LOGFIRE_SEND_TO_LOGFIRE", "1")

    calls: list[str] = []

    def fail_configure(*_args, **_kwargs):
        raise LogfireConfigError("logfire credentials missing")

    monkeypatch.setattr(app_module.logfire, "configure", fail_configure)
    monkeypatch.setattr(app_module.logfire, "instrument_requests", lambda: calls.append("requests"))
    monkeypatch.setattr(app_module.logfire, "instrument_aiohttp_client", lambda: calls.append("aiohttp"))
    monkeypatch.setattr(app_module.logfire, "instrument_pydantic", lambda: calls.append("pydantic"))

    app_instance = app_module.create_app(app_config_factory("logfire"))
    client = app_instance.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert calls == []

    with app_instance.app_context():
        status = app_instance.config["OBSERVABILITY_STATUS"]
        assert status["logfire_available"] is False
        assert "logfire credentials missing" in status["logfire_reason"]
