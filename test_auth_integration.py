#!/usr/bin/env python3
"""Integration tests for the complete authentication system."""

from __future__ import annotations

import contextlib
import os
from typing import Callable, Dict, Generator, List, Optional
from unittest.mock import patch

import pytest

from app import create_app
from auth_providers import auth_manager
from database import db
from models import User
from flask import Flask

TEST_APP_CONFIG: Dict[str, object] = {
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "TESTING": True,
    "WTF_CSRF_ENABLED": False,
}


def build_test_app(config_override: Optional[Dict[str, object]] = None) -> Flask:
    """Create a new Flask application instance configured for testing."""
    config = TEST_APP_CONFIG.copy()
    if config_override:
        config.update(config_override)
    return create_app(config)


def reset_auth_manager_state() -> None:
    """Reset the auth manager to ensure provider detection runs fresh."""
    auth_manager._active_provider = None

    providers = getattr(auth_manager, "providers", {})
    replit_provider = providers.get("replit")
    if replit_provider is not None:
        # Keep the blueprint state in sync with the current environment.
        if not os.environ.get("REPL_ID"):
            setattr(replit_provider, "blueprint", None)
        elif hasattr(replit_provider, "_setup_blueprint"):
            replit_provider._setup_blueprint()


@pytest.fixture
def app_factory() -> Generator[Callable[[Optional[Dict[str, object]]], Flask], None, None]:
    """Provide a factory for creating isolated Flask app instances."""

    created_apps: List[Flask] = []

    def _factory(config_override: Optional[Dict[str, object]] = None) -> Flask:
        reset_auth_manager_state()
        app = build_test_app(config_override)
        created_apps.append(app)
        return app

    yield _factory

    for app in reversed(created_apps):
        with app.app_context():
            engine = db.engine
            db.session.remove()
            db.drop_all()
            engine.dispose()

    reset_auth_manager_state()


@pytest.fixture
def auth_app(app_factory):
    """Create an isolated Flask app for the current test."""

    return app_factory()


@pytest.fixture
def client(auth_app):
    """Provide a Flask test client bound to the isolated app."""

    with auth_app.test_client() as client:
        yield client


@pytest.fixture
def app_context(auth_app) -> Callable[[], contextlib.AbstractContextManager]:
    """Return a callable that yields an application context for the app."""

    @contextlib.contextmanager
    def _context():
        with auth_app.app_context():
            yield

    return _context


@pytest.fixture
def request_context(auth_app) -> Callable[..., contextlib.AbstractContextManager]:
    """Return a callable that yields a request context for the app."""

    @contextlib.contextmanager
    def _context(*args, **kwargs):
        with auth_app.test_request_context(*args, **kwargs):
            yield

    return _context


@pytest.fixture
def reset_auth_manager() -> Generator[Callable[[], None], None, None]:
    """Provide a helper that clears cached provider state before/after tests."""

    reset_auth_manager_state()
    yield reset_auth_manager_state
    reset_auth_manager_state()


def test_auth_manager_detection_local(auth_app, reset_auth_manager):
    """Test that auth manager detects local environment correctly."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        provider = auth_manager.get_active_provider()
        assert provider is not None
        assert provider.get_provider_name() == "Local Development"
        assert auth_manager.is_authentication_available()


def test_auth_manager_detection_replit(auth_app, reset_auth_manager):
    """Test that auth manager detects Replit environment correctly."""

    with patch.dict(
        os.environ,
        {
            "REPL_ID": "test-repl-123",
            "REPL_OWNER": "test-user",
            "REPL_SLUG": "test-project",
        },
    ):
        with patch.object(auth_manager.providers["replit"], "is_available", return_value=True):
            reset_auth_manager()

            provider = auth_manager.get_active_provider()
            assert provider.get_provider_name() == "Replit"
            assert auth_manager.is_authentication_available()


def test_local_auth_flow(auth_app, client, request_context, app_context, reset_auth_manager):
    """Test complete local authentication flow."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        with request_context("/"):
            login_url = auth_manager.get_login_url()
            assert "/auth/login" in login_url

        response = client.post("/auth/login")
        assert response.status_code == 302
        assert "/dashboard" in response.location

        with app_context():
            users = User.query.all()
            assert len(users) == 1
            user = users[0]
            assert user.id.startswith("local_")
            assert user.is_paid
            assert user.current_terms_accepted


def test_protected_route_access(auth_app, client, reset_auth_manager):
    """Test that protected routes work with authentication."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/auth/login" in response.location

        response = client.post("/auth/login")
        assert response.status_code == 302

        response = client.get("/dashboard")
        assert response.status_code == 302  # Redirects to content
        assert "/content" in response.location


def test_logout_flow(auth_app, client, reset_auth_manager):
    """Test complete logout flow."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        response = client.post("/auth/login")
        assert response.status_code == 302

        response = client.get("/auth/logout")
        assert response.status_code == 302
        assert "/" in response.location

        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/auth/login" in response.location


def test_registration_flow(auth_app, client, app_context, reset_auth_manager):
    """Test complete registration flow."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        response = client.post(
            "/auth/register",
            data={
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert response.status_code == 302
        assert "/dashboard" in response.location

        with app_context():
            users = User.query.all()
            assert len(users) == 1
            user = users[0]
            assert user.email == "test@example.com"
            assert user.first_name == "Test"
            assert user.last_name == "User"


def test_template_integration(auth_app, client, request_context, reset_auth_manager):
    """Test that templates use the correct authentication URLs."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        response = client.get("/")
        assert response.status_code == 200
        assert b"/auth/login" in response.data

        with request_context("/"):
            assert b'href="/auth/login"' in response.data


def test_switch_from_local_to_replit(auth_app, reset_auth_manager):
    """Test switching from local to Replit authentication."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()
        local_provider = auth_manager.get_active_provider()
        assert local_provider.get_provider_name() == "Local Development"

    with patch.dict(
        os.environ,
        {
            "REPL_ID": "test-repl-456",
            "REPL_OWNER": "test-user-2",
            "REPL_SLUG": "test-project-2",
        },
    ):
        with patch.object(auth_manager.providers["replit"], "is_available", return_value=True):
            reset_auth_manager()
            replit_provider = auth_manager.get_active_provider()
            assert replit_provider.get_provider_name() == "Replit"


def test_switch_from_replit_to_local(auth_app, reset_auth_manager):
    """Test switching from Replit to local authentication."""

    with patch.dict(
        os.environ,
        {
            "REPL_ID": "test-repl-789",
            "REPL_OWNER": "test-user-3",
            "REPL_SLUG": "test-project-3",
        },
    ):
        with patch.object(auth_manager.providers["replit"], "is_available", return_value=True):
            reset_auth_manager()
            replit_provider = auth_manager.get_active_provider()
            assert replit_provider.get_provider_name() == "Replit"

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()
        local_provider = auth_manager.get_active_provider()
        assert local_provider.get_provider_name() == "Local Development"


def test_auth_manager_no_providers_available(auth_app, reset_auth_manager):
    """Test auth manager when no providers are available."""

    with patch.dict(os.environ, {}, clear=True):
        reset_auth_manager()

        with patch.object(auth_manager.providers["replit"], "is_available", return_value=False):
            with patch.object(auth_manager.providers["local"], "is_available", return_value=False):
                provider = auth_manager.get_active_provider()
                assert provider is None
                assert not auth_manager.is_authentication_available()
                assert auth_manager.get_provider_name() == "None"


def test_invalid_login_url_when_no_provider(auth_app, request_context, reset_auth_manager):
    """Test that login URL handling works when no provider is available."""

    with request_context("/"):
        with patch.object(auth_manager.providers["local"], "is_available", return_value=False):
            with patch.object(auth_manager.providers["replit"], "is_available", return_value=False):
                reset_auth_manager()

                login_url = auth_manager.get_login_url()
                assert "/" in login_url  # May be full URL due to app config
