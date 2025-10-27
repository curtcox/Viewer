"""Tests that ensure the Flask application can start successfully."""

from __future__ import annotations

from pathlib import Path

import pytest
from logfire.exceptions import LogfireConfigError
from sqlalchemy import inspect

import app as app_module
from database import db


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


def test_create_app_handles_logfire_instrumentation_errors(
    monkeypatch: pytest.MonkeyPatch, app_config_factory
):
    """Instrumentation failures should be logged but not crash startup."""

    monkeypatch.setenv("LOGFIRE_SEND_TO_LOGFIRE", "1")

    instrumentation_calls: list[str] = []

    monkeypatch.setattr(app_module.logfire, "configure", lambda *_, **__: None)
    monkeypatch.setattr(
        app_module.logfire,
        "instrument_requests",
        lambda: (_ for _ in ()).throw(ModuleNotFoundError("requests not installed")),
    )
    monkeypatch.setattr(
        app_module.logfire,
        "instrument_aiohttp_client",
        lambda: instrumentation_calls.append("aiohttp"),
    )
    monkeypatch.setattr(
        app_module.logfire,
        "instrument_pydantic",
        lambda: instrumentation_calls.append("pydantic"),
    )

    app_instance = app_module.create_app(app_config_factory("instrument"))

    client = app_instance.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert instrumentation_calls == []

    with app_instance.app_context():
        status = app_instance.config["OBSERVABILITY_STATUS"]
        assert status["logfire_available"] is False
        assert "requests instrumentation failed" in status["logfire_reason"]


def test_create_app_creates_alias_definition_column(
    monkeypatch: pytest.MonkeyPatch, app_config_factory
):
    """New databases should include the alias.definition column without migration."""

    monkeypatch.delenv("LOGFIRE_SEND_TO_LOGFIRE", raising=False)

    app_instance = app_module.create_app(app_config_factory("modern-alias"))
    client = app_instance.test_client()

    response = client.get("/")

    assert response.status_code == 200

    with app_instance.app_context():
        inspector = inspect(db.engine)
        column_names = {column["name"] for column in inspector.get_columns("alias")}
        assert "definition" in column_names
