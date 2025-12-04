"""Integration coverage for the server events history page."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from cid_presenter import cid_path
from database import db
from models import CID, ServerInvocation

pytestmark = pytest.mark.integration


def test_server_events_page_lists_recent_invocations(
    client,
    integration_app,
):
    """The server events page should render recorded invocations."""

    request_cid = "bafyrequestcid123"
    referer_url = "https://example.com/dashboard"

    with integration_app.app_context():
        cid_record = CID(
            path=cid_path(request_cid),
            file_data=json.dumps(
                {
                    "headers": {
                        "Referer": referer_url,
                    }
                }
            ).encode("utf-8"),
        )
        invocation = ServerInvocation(
            server_name="weather",
            result_cid="bafyresultcid456",
            servers_cid="bafyserverscid789",
            request_details_cid=request_cid,
            invocation_cid="bafyinvocationcid000",
        )

        db.session.add(cid_record)
        db.session.add(invocation)
        db.session.commit()

    response = client.get("/server_events")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Server Events" in page
    assert "Total Events" in page
    assert "1" in page
    assert "weather" in page
    assert referer_url in page


def test_server_events_page_filters_by_time(
    client,
    integration_app,
):
    """The server events page should respect time range filters."""

    with integration_app.app_context():
        now = datetime(2025, 2, 28, 15, 35, 36, tzinfo=timezone.utc)
        recent = ServerInvocation(server_name="recent", result_cid="recent-cid")
        recent.invoked_at = now
        old = ServerInvocation(server_name="old", result_cid="old-cid")
        old.invoked_at = now - timedelta(hours=5)

        db.session.add_all([recent, old])
        db.session.commit()

    start_param = now.strftime("%Y/%m/%d %H:%M:%S")
    response = client.get(f"/server_events?start={start_param.replace(' ', '%20')}")

    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "recent" in page
    assert "old" not in page
    assert start_param in page
    assert "timestamp-valid" in page
