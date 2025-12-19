"""Tests that ensure the Flask application can start successfully."""

from __future__ import annotations

from pathlib import Path

import pytest
from logfire.exceptions import LogfireConfigError
from sqlalchemy import inspect

import app as app_module
from cid_utils import generate_cid
from db_access import get_cid_by_path
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


def test_create_app_uses_fallback_secret_key_when_session_secret_empty(
    monkeypatch: pytest.MonkeyPatch, app_config_factory
):
    monkeypatch.delenv("LOGFIRE_SEND_TO_LOGFIRE", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "")

    app_instance = app_module.create_app(app_config_factory("empty-session-secret"))

    assert app_instance.config.get("SECRET_KEY")


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
    assert not calls

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
    assert not instrumentation_calls

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


def test_create_app_loads_cids_from_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, app_config_factory
) -> None:
    """CID fixtures on disk should be imported into the database."""

    monkeypatch.delenv("LOGFIRE_SEND_TO_LOGFIRE", raising=False)

    content = b"example payload"
    cid_value = generate_cid(content)

    cid_dir = tmp_path / "cids"
    cid_dir.mkdir()
    (cid_dir / cid_value).write_bytes(content)

    config = app_config_factory("cid-load")
    config["CID_DIRECTORY"] = str(cid_dir)

    app_instance = app_module.create_app(config)

    with app_instance.app_context():
        record = get_cid_by_path(f"/{cid_value}")
        assert record is not None
        assert record.file_data == content


def test_create_app_exits_on_cid_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, app_config_factory
) -> None:
    """Startup should store error in config and show 500 page if CID filename is invalid or doesn't match contents."""

    monkeypatch.delenv("LOGFIRE_SEND_TO_LOGFIRE", raising=False)

    cid_dir = tmp_path / "cids"
    cid_dir.mkdir()
    (cid_dir / "not-a-cid").write_bytes(b"data")

    config = app_config_factory("cid-mismatch")
    config["CID_DIRECTORY"] = str(cid_dir)

    # App should be created successfully, but with error stored in config
    app_instance = app_module.create_app(config)

    # Check that the error is stored in config
    with app_instance.app_context():
        cid_error = app_instance.config.get("CID_LOAD_ERROR")
        assert cid_error is not None
        assert "not-a-cid" in cid_error
        assert "not a valid normalized CID" in cid_error

    # Check that requests return 500 error page with the error message
    client = app_instance.test_client()
    response = client.get("/")
    assert response.status_code == 500
    response_text = response.get_data(as_text=True)
    # The error message should contain information about the invalid CID
    assert "not-a-cid" in response_text
    assert "not a valid normalized CID" in response_text
