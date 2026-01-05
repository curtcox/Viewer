from __future__ import annotations

from reference.templates.servers.definitions import amplitude


def test_requires_api_key():
    result = amplitude.main()
    assert result["output"]["error"] == "Missing AMPLITUDE_API_KEY"
    assert result["output"]["status_code"] == 401


def test_requires_user_or_device_id():
    result = amplitude.main(AMPLITUDE_API_KEY="key")
    assert "Either user_id or device_id is required" in result["output"]["error"]["message"]


def test_track_requires_event_type():
    result = amplitude.main(
        operation="track",
        user_id="user123",
        AMPLITUDE_API_KEY="key",
    )
    assert "event_type is required" in result["output"]["error"]["message"]


def test_invalid_operation():
    result = amplitude.main(
        operation="invalid",
        user_id="user123",
        AMPLITUDE_API_KEY="key",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_track():
    result = amplitude.main(
        operation="track",
        event_type="Button Clicked",
        user_id="user123",
        event_properties='{"button": "signup"}',
        AMPLITUDE_API_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "track"
    assert result["output"]["event_type"] == "Button Clicked"
    assert result["output"]["user_id"] == "user123"
    assert result["output"]["method"] == "POST"


def test_dry_run_identify():
    result = amplitude.main(
        operation="identify",
        user_id="user123",
        user_properties='{"email": "user@example.com"}',
        AMPLITUDE_API_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "identify"


def test_with_device_id():
    result = amplitude.main(
        operation="track",
        event_type="App Opened",
        device_id="device123",
        AMPLITUDE_API_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["user_id"] == "device123"


def test_invalid_properties_json():
    result = amplitude.main(
        operation="track",
        event_type="Test",
        user_id="user123",
        event_properties='invalid json',
        AMPLITUDE_API_KEY="key",
        dry_run=True,
    )
    assert "Invalid JSON" in result["output"]["error"]["message"]


def test_url_structure():
    result = amplitude.main(
        operation="track",
        event_type="Test Event",
        user_id="user123",
        AMPLITUDE_API_KEY="key",
        dry_run=True,
    )
    assert "api2.amplitude.com" in result["output"]["url"]
