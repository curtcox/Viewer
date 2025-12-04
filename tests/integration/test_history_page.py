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
):
    """The history page should render recorded page views for the user."""

    with integration_app.app_context():
        now = datetime.now(timezone.utc)
        page_views = [
            PageView(
                path="/profile",
                method="GET",
                viewed_at=now - timedelta(minutes=5),
            ),
            PageView(
                path="/upload",
                method="POST",
                viewed_at=now - timedelta(minutes=1),
            ),
        ]
        db.session.add_all(page_views)
        db.session.commit()

    response = client.get("/history")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Browse History" in page
    assert "Recent Activity" in page
    assert "/profile" in page
    assert "/upload" in page
    assert "POST" in page


def test_history_page_applies_query_time_filters(client, integration_app):
    """Filtering by time bounds should limit results and echo inputs."""

    with integration_app.app_context():
        now = datetime.now(timezone.utc)
        page_views = [
            PageView(path="/kept", method="GET", viewed_at=now - timedelta(minutes=1)),
            PageView(path="/omitted", method="GET", viewed_at=now - timedelta(hours=2)),
        ]
        db.session.add_all(page_views)
        db.session.commit()

    start = now - timedelta(minutes=5)
    end = now + timedelta(minutes=5)
    start_param = start.strftime("%Y/%m/%d %H:%M:%S")
    end_param = end.strftime("%Y/%m/%d %H:%M:%S")

    response = client.get(
        f"/history?start={start_param.replace(' ', '%20')}&end={end_param.replace(' ', '%20')}"
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "/kept" in page
    assert "/omitted" not in page
    assert start_param in page
    assert end_param in page
