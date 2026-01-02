from __future__ import annotations

from reference_templates.servers.definitions import mixpanel


def test_requires_token():
    result = mixpanel.main()
    assert result["output"]["error"] == "Missing MIXPANEL_TOKEN"
    assert result["output"]["status_code"] == 401


def test_requires_distinct_id():
    result = mixpanel.main(MIXPANEL_TOKEN="token")
    assert "distinct_id is required" in result["output"]["error"]["message"]


def test_track_requires_event():
    result = mixpanel.main(
        operation="track",
        distinct_id="user123",
        MIXPANEL_TOKEN="token",
    )
    assert "Event name is required" in result["output"]["error"]["message"]


def test_invalid_operation():
    result = mixpanel.main(
        operation="invalid",
        distinct_id="user123",
        MIXPANEL_TOKEN="token",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_track():
    result = mixpanel.main(
        operation="track",
        event="Button Clicked",
        distinct_id="user123",
        properties='{"button": "signup"}',
        MIXPANEL_TOKEN="token",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "track"
    assert result["output"]["event"] == "Button Clicked"
    assert result["output"]["distinct_id"] == "user123"
    assert result["output"]["method"] == "POST"


def test_dry_run_engage():
    result = mixpanel.main(
        operation="engage",
        distinct_id="user123",
        set_properties='{"email": "user@example.com"}',
        MIXPANEL_TOKEN="token",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "engage"


def test_dry_run_import():
    result = mixpanel.main(
        operation="import",
        event="Historical Event",
        distinct_id="user123",
        MIXPANEL_TOKEN="token",
        MIXPANEL_API_SECRET="secret",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "import"


def test_invalid_properties_json():
    result = mixpanel.main(
        operation="track",
        event="Test",
        distinct_id="user123",
        properties='invalid json',
        MIXPANEL_TOKEN="token",
        dry_run=True,
    )
    assert "Invalid JSON" in result["output"]["error"]["message"]


def test_url_structure():
    result = mixpanel.main(
        operation="track",
        event="Test Event",
        distinct_id="user123",
        MIXPANEL_TOKEN="token",
        dry_run=True,
    )
    assert "api.mixpanel.com" in result["output"]["url"]
