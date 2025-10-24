"""Integration tests for the history page."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from database import db
from models import PageView

pytestmark = pytest.mark.integration



def test_history_page_displays_recent_activity(
    client,
    integration_app,
    login_default_user,
):
    """The history page should render recorded page views for the user."""

    with integration_app.app_context():
        now = datetime.now(timezone.utc)
        page_views = [
            PageView(
                user_id="default-user",
                path="/profile",
                method="GET",
                viewed_at=now - timedelta(minutes=5),
            ),
            PageView(
                user_id="default-user",
                path="/upload",
                method="POST",
                viewed_at=now - timedelta(minutes=1),
            ),
        ]
        db.session.add_all(page_views)
        db.session.commit()

    login_default_user()

    response = client.get("/history")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Browse History" in page
    assert "Recent Activity" in page
    assert "/profile" in page
    assert "/upload" in page
    assert "POST" in page
