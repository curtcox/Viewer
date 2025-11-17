"""Integration coverage for the server events history page."""
from __future__ import annotations

import json

import pytest

from cid_presenter import cid_path
from database import db
from models import CID, ServerInvocation

pytestmark = pytest.mark.integration


def test_server_events_page_lists_recent_invocations(
    client,
    integration_app,
    login_default_user,
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

    login_default_user()

    response = client.get("/server_events")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Server Events" in page
    assert "Total Events" in page
    assert "1" in page
    assert "weather" in page
    assert referer_url in page
