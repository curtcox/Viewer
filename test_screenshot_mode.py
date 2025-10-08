import pytest

from app import create_app


@pytest.fixture(autouse=True)
def reset_screenshot_env(monkeypatch):
    monkeypatch.delenv('SCREENSHOT_MODE', raising=False)


def _make_client(**config):
    app = create_app({'TESTING': True, **config})
    return app.test_client()


def test_screenshot_route_disabled_by_default():
    client = _make_client()
    response = client.get('/_screenshot/cid-demo')
    assert response.status_code == 404


def test_screenshot_route_enabled():
    client = _make_client(SCREENSHOT_MODE=True)
    response = client.get('/_screenshot/cid-demo')
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert 'CID Screenshot Demo' in body
    assert '#bafybeigd...' in body
    assert 'View metadata' in body


def test_uploads_screenshot_routes_require_flag():
    client = _make_client()
    assert client.get('/_screenshot/uploads').status_code == 404
    assert client.get('/_screenshot/server-events').status_code == 404


def test_uploads_screenshot_routes_render_samples():
    client = _make_client(SCREENSHOT_MODE=True)

    uploads_response = client.get('/_screenshot/uploads')
    assert uploads_response.status_code == 200
    uploads_body = uploads_response.get_data(as_text=True)
    assert 'Your Files' in uploads_body
    assert '#bafybeigd...' in uploads_body
    assert 'Markdown sample text...' in uploads_body

    events_response = client.get('/_screenshot/server-events')
    assert events_response.status_code == 200
    events_body = events_response.get_data(as_text=True)
    assert 'Server Events' in events_body
    assert '#bafybeigd...' in events_body
    assert 'billing-reporter' in events_body
