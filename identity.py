"""Provide a default user identity for the application.

The application no longer manages authentication internally. Instead it
always operates on a single default user record so all existing logic that
expects ``current_user`` continues to function without conditional login
checks.
"""
from __future__ import annotations

from typing import Optional

from flask import g, has_request_context, session
from werkzeug.local import LocalProxy

from ai_defaults import ensure_ai_stub_for_user
from db_access import get_user_by_id, load_user_by_id, save_entity
from models import User

_DEFAULT_USER_ID = "default-user"
_DEFAULT_EMAIL = "default@example.com"
_DEFAULT_FIRST_NAME = "Viewer"
_DEFAULT_LAST_NAME = "User"

_cached_user: Optional[User] = None


def _ensure_default_user() -> User:
    """Return the singleton default user, creating it if necessary."""

    user = get_user_by_id(_DEFAULT_USER_ID)
    if user is None:
        user = User(
            id=_DEFAULT_USER_ID,
            email=_DEFAULT_EMAIL,
            first_name=_DEFAULT_FIRST_NAME,
            last_name=_DEFAULT_LAST_NAME,
            is_paid=True,
            current_terms_accepted=True,
        )
        save_entity(user)
        ensure_ai_stub_for_user(user.id)
        return user

    # Ensure legacy flags remain enabled so existing UI behaves as expected.
    updated = False
    if not getattr(user, "is_paid", False):
        user.is_paid = True
        updated = True
    if not getattr(user, "current_terms_accepted", False):
        user.current_terms_accepted = True
        updated = True
    if updated:
        save_entity(user)
    return user


def ensure_default_user() -> User:
    """Public helper to ensure the default user exists."""

    global _cached_user
    user = _ensure_default_user()
    _cached_user = user
    return user


def _load_current_user() -> User:
    """Return the application user for the active context."""

    global _cached_user

    if has_request_context():
        requested_user_id = session.get("_user_id")
        user = getattr(g, "_default_user", None)

        if requested_user_id:
            if not user or getattr(user, "id", None) != requested_user_id:
                user = load_user_by_id(requested_user_id)
                if user is None:
                    user = _ensure_default_user()
                g._default_user = user
        else:
            if user is None:
                user = _ensure_default_user()
                g._default_user = user

        _cached_user = user
        return user

    if _cached_user is None:
        _cached_user = _ensure_default_user()
    return _cached_user


current_user: User = LocalProxy(_load_current_user)

__all__ = ["current_user", "ensure_default_user"]
