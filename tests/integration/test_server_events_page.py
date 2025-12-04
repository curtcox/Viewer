"""Integration coverage for the server events history page."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from ai_defaults import ensure_ai_stub
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


def test_ai_request_details_capture_json_body(client, integration_app):
    """AI invocations should record the JSON payload in request details."""

    payload = {
        "request_text": "Expand the example",
        "original_text": "Existing server definition",
        "target_label": "server definition",
        "context_data": {"form": "server_form"},
        "form_summary": {"definition": "Existing server definition"},
    }

    with integration_app.app_context():
        ensure_ai_stub()
        ServerInvocation.query.delete()
        CID.query.delete()
        db.session.commit()

    response = client.post("/ai", json=payload, follow_redirects=True)
    assert response.status_code == 200

    with integration_app.app_context():
        invocation = (
            ServerInvocation.query.filter_by(server_name="ai_stub")
            .order_by(ServerInvocation.invoked_at.desc())
            .first()
        )

        assert invocation is not None
        assert invocation.request_details_cid is not None

        request_cid_path = cid_path(invocation.request_details_cid)
        cid_record = CID.query.filter_by(path=request_cid_path).first()
        assert cid_record is not None

        request_data = json.loads(cid_record.file_data.decode("utf-8"))

        assert request_data.get("json") == payload
        assert "request_text" in request_data.get("body", "")
