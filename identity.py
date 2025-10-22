"""Provide a lightweight external user identity for the application."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from flask import g, has_request_context, session
from werkzeug.local import LocalProxy

from ai_defaults import ensure_ai_stub_for_user

_DEFAULT_USER_ID = "default-user"
_DEFAULT_EMAIL = "default@example.com"
_DEFAULT_FIRST_NAME = "Viewer"
_DEFAULT_LAST_NAME = "User"


@dataclass
class ExternalUser:
    """Representation of an externally managed user account."""

    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_paid: bool = True
    payment_expires_at: Optional[datetime] = None
    current_terms_accepted: bool = True

    def has_access(self) -> bool:
        """Return whether the user has access based on subscription metadata."""

        if not self.is_paid or not self.current_terms_accepted:
            return False

        if self.payment_expires_at is None:
            return True

        expires = self.payment_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > datetime.now(timezone.utc)

    @property
    def username(self) -> str:
        """Compatibility helper used by templates for display names."""

        return self.first_name or self.email or self.id


_default_user: Optional[ExternalUser] = None
_cached_user: Optional[ExternalUser] = None


def _create_default_user() -> ExternalUser:
    """Initialise the singleton default user."""

    user = ExternalUser(
        id=_DEFAULT_USER_ID,
        email=_DEFAULT_EMAIL,
        first_name=_DEFAULT_FIRST_NAME,
        last_name=_DEFAULT_LAST_NAME,
        is_paid=True,
        current_terms_accepted=True,
    )
    ensure_ai_stub_for_user(user.id)
    return user


def ensure_default_user() -> ExternalUser:
    """Public helper to ensure the default user exists."""

    global _default_user, _cached_user
    if _default_user is None:
        _default_user = _create_default_user()
    else:
        # Test suites may create fresh in-memory databases between calls while the
        # in-process default user instance remains cached. Make sure the default
        # AI stub resources are present for the active database on every
        # invocation.
        ensure_ai_stub_for_user(_default_user.id)
    _cached_user = _default_user
    return _default_user


def _load_current_user() -> ExternalUser:
    """Return the current user for the active request or global context."""

    global _cached_user

    if has_request_context():
        requested_user_id = session.get("_user_id")
        user: Optional[ExternalUser] = getattr(g, "_default_user", None)

        if requested_user_id:
            if not user or getattr(user, "id", None) != requested_user_id:
                user = ExternalUser(
                    id=requested_user_id,
                    is_paid=True,
                    current_terms_accepted=True,
                )
                ensure_ai_stub_for_user(user.id)
                g._default_user = user
        else:
            if user is None:
                user = ensure_default_user()
                g._default_user = user

        _cached_user = user
        return user

    if _cached_user is None:
        _cached_user = ensure_default_user()
    return _cached_user


current_user: ExternalUser = LocalProxy(_load_current_user)

__all__ = ["ExternalUser", "current_user", "ensure_default_user"]
