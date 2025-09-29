"""Helpers for configuring optional Logfire and LangSmith integrations."""

from __future__ import annotations

import importlib
import inspect
import logging
import os
from typing import Any, Dict, Optional

from flask import Flask

try:
    from sqlalchemy.engine import Engine
except ImportError:  # pragma: no cover - SQLAlchemy is part of requirements
    Engine = Any  # type: ignore[misc, assignment]


ObservabilityStatus = Dict[str, Any]


def _call_with_supported_kwargs(func: Any, candidate_kwargs: Dict[str, Any]) -> Any:
    """Invoke *func* with only keyword arguments it supports."""

    if not callable(func):
        raise TypeError("Expected a callable object")

    signature = None
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):  # pragma: no cover - extremely uncommon
        return func(**candidate_kwargs)

    supported = {
        name: value
        for name, value in candidate_kwargs.items()
        if value is not None and name in signature.parameters
    }
    return func(**supported)


def _initial_status() -> ObservabilityStatus:
    """Return the default observability status dictionary."""

    return {
        "logfire_available": False,
        "logfire_project_url": os.getenv("LOGFIRE_PROJECT_URL") or None,
        "logfire_reason": None,
        "langsmith_available": False,
        "langsmith_project_url": os.getenv("LANGSMITH_PROJECT_URL") or None,
        "langsmith_reason": None,
    }


def initialize_observability(app: Flask, engine: Optional[Engine] = None) -> ObservabilityStatus:
    """Configure Logfire and LangSmith integrations if available.

    Parameters
    ----------
    app:
        The Flask application instance. Used for logging and instrumentation.
    engine:
        Optional SQLAlchemy engine used when Logfire exposes SQLAlchemy instrumentation.

    Returns
    -------
    ObservabilityStatus
        A dictionary describing the availability of Logfire and LangSmith integrations.
    """

    logger = app.logger if app else logging.getLogger(__name__)
    status = _initial_status()

    api_key = os.getenv("LOGFIRE_API_KEY")
    if not api_key:
        status["logfire_reason"] = "LOGFIRE_API_KEY is not set"
        logger.info("Logfire support disabled: %s", status["logfire_reason"])
        _record_langsmith_disabled(status, logger, "Logfire is not configured")
        return status

    try:
        logfire_module = importlib.import_module("logfire")
    except ImportError as exc:  # pragma: no cover - depends on environment
        status["logfire_reason"] = "logfire package is not installed"
        logger.info("Logfire support disabled: %s", status["logfire_reason"])
        _record_langsmith_disabled(status, logger, "Logfire package missing")
        return status

    configure_fn = getattr(logfire_module, "configure", None)
    if not callable(configure_fn):
        status["logfire_reason"] = "Logfire configure() entrypoint not available"
        logger.info("Logfire support disabled: %s", status["logfire_reason"])
        _record_langsmith_disabled(status, logger, "Logfire configuration entrypoint missing")
        return status

    configure_kwargs = {
        "api_key": api_key,
        "service_name": os.getenv("LOGFIRE_SERVICE_NAME", "secureapp"),
        "environment": os.getenv("LOGFIRE_ENVIRONMENT", "development"),
    }

    try:
        _call_with_supported_kwargs(configure_fn, configure_kwargs)
    except Exception as exc:  # pragma: no cover - depends on logfire internals
        status["logfire_reason"] = f"Failed to configure Logfire: {exc}"
        logger.exception("Failed to configure Logfire")
        _record_langsmith_disabled(status, logger, "Logfire configuration failed")
        return status

    status["logfire_available"] = True
    status["logfire_reason"] = None
    logger.info("Logfire support enabled for service '%s'", configure_kwargs["service_name"])

    _instrument_flask(logfire_module, app, logger)
    _instrument_sqlalchemy(logfire_module, engine, logger)

    _configure_langsmith(logfire_module, status, logger)

    return status


def _record_langsmith_disabled(status: ObservabilityStatus, logger: logging.Logger, reason: str) -> None:
    """Store consistent LangSmith disabled status information."""

    status["langsmith_available"] = False
    status["langsmith_reason"] = reason
    if reason:
        logger.info("LangSmith support disabled: %s", reason)


def _instrument_flask(logfire_module: Any, app: Flask, logger: logging.Logger) -> None:
    """Instrument Flask with Logfire when supported."""

    flask_instrumenter = getattr(logfire_module, "instrument_flask", None)
    if callable(flask_instrumenter):
        try:
            _call_with_supported_kwargs(flask_instrumenter, {"app": app})
            logger.info("Logfire Flask instrumentation enabled")
        except Exception:  # pragma: no cover - depends on logfire internals
            logger.exception("Failed to instrument Flask with Logfire")
    else:
        logger.debug("Logfire Flask instrumentation hook not available")


def _instrument_sqlalchemy(logfire_module: Any, engine: Optional[Engine], logger: logging.Logger) -> None:
    """Instrument SQLAlchemy with Logfire when supported."""

    if engine is None:
        logger.debug("SQLAlchemy engine not available for Logfire instrumentation")
        return

    sqlalchemy_instrumenter = getattr(logfire_module, "instrument_sqlalchemy", None)
    if callable(sqlalchemy_instrumenter):
        try:
            _call_with_supported_kwargs(sqlalchemy_instrumenter, {"engine": engine})
            logger.info("Logfire SQLAlchemy instrumentation enabled")
        except Exception:  # pragma: no cover - depends on logfire internals
            logger.exception("Failed to instrument SQLAlchemy with Logfire")
        return

    try:
        sqlalchemy_module = importlib.import_module("logfire.integrations.sqlalchemy")
    except ImportError:  # pragma: no cover - depends on logfire extras
        logger.debug("Logfire SQLAlchemy integration module not available")
        return

    sqlalchemy_instrumenter = getattr(sqlalchemy_module, "instrument_sqlalchemy", None)
    if callable(sqlalchemy_instrumenter):
        try:
            _call_with_supported_kwargs(sqlalchemy_instrumenter, {"engine": engine})
            logger.info("Logfire SQLAlchemy instrumentation enabled via integration module")
        except Exception:  # pragma: no cover - depends on logfire internals
            logger.exception("Failed to instrument SQLAlchemy via Logfire integration module")
    else:
        logger.debug("Logfire SQLAlchemy instrumentation function not found")


def _configure_langsmith(logfire_module: Any, status: ObservabilityStatus, logger: logging.Logger) -> None:
    """Enable LangSmith support via Logfire when possible."""

    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    if not langsmith_api_key:
        _record_langsmith_disabled(status, logger, "LANGSMITH_API_KEY is not set")
        return

    langsmith_project_url = status.get("langsmith_project_url")
    if not langsmith_project_url:
        logger.info("LangSmith project URL not provided; links will be disabled")

    instrumenter = getattr(logfire_module, "instrument_langchain", None)
    if not callable(instrumenter):
        try:
            langchain_module = importlib.import_module("logfire.integrations.langchain")
            instrumenter = getattr(langchain_module, "instrument_langchain", None)
        except ImportError:
            instrumenter = None

    if not callable(instrumenter):
        _record_langsmith_disabled(status, logger, "Logfire LangSmith integration not available")
        return

    try:
        _call_with_supported_kwargs(
            instrumenter,
            {
                "api_key": langsmith_api_key,
                "project_name": os.getenv("LANGSMITH_PROJECT") or None,
            },
        )
        status["langsmith_available"] = True
        status["langsmith_reason"] = None
        logger.info("LangSmith support enabled via Logfire integration")
    except Exception as exc:  # pragma: no cover - depends on logfire internals
        status["langsmith_available"] = False
        status["langsmith_reason"] = f"Failed to enable LangSmith integration: {exc}"
        logger.exception("Failed to enable LangSmith integration via Logfire")


__all__ = ["initialize_observability", "ObservabilityStatus"]
