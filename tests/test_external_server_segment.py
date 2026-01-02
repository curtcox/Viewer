from __future__ import annotations

from reference_templates.servers.definitions import segment


def test_requires_write_key():
    result = segment.main()
    assert result["output"]["error"] == "Missing SEGMENT_WRITE_KEY"
    assert result["output"]["status_code"] == 401


def test_requires_user_or_anonymous_id():
    result = segment.main(SEGMENT_WRITE_KEY="key")
    assert "Either user_id or anonymous_id is required" in result["output"]["error"]["message"]


def test_track_requires_event():
    result = segment.main(
        operation="track",
        user_id="user123",
        SEGMENT_WRITE_KEY="key",
    )
    assert "Event name is required" in result["output"]["error"]["message"]


def test_invalid_operation():
    result = segment.main(
        operation="invalid",
        user_id="user123",
        SEGMENT_WRITE_KEY="key",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_track():
    result = segment.main(
        operation="track",
        event="Button Clicked",
        user_id="user123",
        properties='{"button": "signup"}',
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "track"
    assert result["output"]["event"] == "Button Clicked"
    assert result["output"]["user_id"] == "user123"
    assert result["output"]["method"] == "POST"


def test_dry_run_identify():
    result = segment.main(
        operation="identify",
        user_id="user123",
        traits='{"email": "user@example.com"}',
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "identify"


def test_dry_run_page():
    result = segment.main(
        operation="page",
        event="Home",
        user_id="user123",
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "page"


def test_dry_run_screen():
    result = segment.main(
        operation="screen",
        event="Main Screen",
        user_id="user123",
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "screen"


def test_dry_run_group():
    result = segment.main(
        operation="group",
        event="company123",
        user_id="user123",
        traits='{"name": "Acme Inc"}',
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "group"


def test_with_anonymous_id():
    result = segment.main(
        operation="track",
        event="Page View",
        anonymous_id="anon123",
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["user_id"] == "anon123"


def test_invalid_properties_json():
    result = segment.main(
        operation="track",
        event="Test",
        user_id="user123",
        properties='invalid json',
        SEGMENT_WRITE_KEY="key",
        dry_run=True,
    )
    assert "Invalid JSON" in result["output"]["error"]["message"]
