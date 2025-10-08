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
