import requests
from reference_templates.servers.definitions import front

class DummyResponse:
    def __init__(self, status_code: int = 200, json_data=None, text: str = ""):
        self.status_code, self._json_data, self.text, self.ok = status_code, json_data if json_data is not None else {}, text, status_code < 400
    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data

class FakeClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response, self.exc, self.calls = response, exc, []
    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response
    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

def test_missing_api_token(): assert front.main(FRONT_API_TOKEN="", dry_run=False)["output"]["error"] == "Missing FRONT_API_TOKEN"
def test_invalid_operation(): assert front.main(FRONT_API_TOKEN="key", operation="unknown")["output"]["error"]["message"] == "Unsupported operation"
def test_get_conversation_requires_id(): assert front.main(FRONT_API_TOKEN="key", operation="get_conversation")["output"]["error"]["message"] == "Missing required conversation_id"
def test_send_message_requires_fields():
    assert front.main(FRONT_API_TOKEN="key", operation="send_message", to=["a@test.com"], body="hi")["output"]["error"]["message"] == "Missing required channel_id"
    assert front.main(FRONT_API_TOKEN="key", operation="send_message", channel_id="ch1", body="hi")["output"]["error"]["message"] == "Missing required to (list of emails)"
    assert front.main(FRONT_API_TOKEN="key", operation="send_message", channel_id="ch1", to=["a@test.com"])["output"]["error"]["message"] == "Missing required body"
def test_get_teammate_requires_id(): assert front.main(FRONT_API_TOKEN="key", operation="get_teammate")["output"]["error"]["message"] == "Missing required teammate_id"
def test_dry_run_preview():
    result = front.main(FRONT_API_TOKEN="key", operation="list_conversations", dry_run=True)
    assert result["output"]["preview"]["operation"] == "list_conversations"
    assert result["output"]["preview"]["url"] == "https://api2.frontapp.com/conversations"
def test_list_conversations_success():
    client = FakeClient(response=DummyResponse(200, {"_results": [{"id": "1"}]}))
    result = front.main(FRONT_API_TOKEN="key", operation="list_conversations", dry_run=False, client=client)
    assert "_results" in result["output"]
def test_send_message_success():
    client = FakeClient(response=DummyResponse(202, {"message_uid": "abc"}))
    result = front.main(FRONT_API_TOKEN="key", operation="send_message", channel_id="ch1", to=["user@test.com"], body="Hello", dry_run=False, client=client)
    assert "message_uid" in result["output"]
def test_request_exception():
    client = FakeClient(exc=requests.RequestException("Error"))
    assert "Front request failed" in front.main(FRONT_API_TOKEN="key", dry_run=False, client=client)["output"]["error"]
def test_invalid_json():
    client = FakeClient(response=DummyResponse(200, ValueError("Bad"), "<html>"))
    assert front.main(FRONT_API_TOKEN="key", dry_run=False, client=client)["output"]["error"] == "Invalid JSON response"
def test_api_error():
    client = FakeClient(response=DummyResponse(401, {"message": "Unauthorized"}))
    result = front.main(FRONT_API_TOKEN="key", dry_run=False, client=client)
    assert result["output"]["error"] == "Unauthorized"
