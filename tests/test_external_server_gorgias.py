import requests
from reference_templates.servers.definitions import gorgias

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
    def put(self, url: str, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        if self.exc:
            raise self.exc
        return self.response

def test_missing_required(): 
    assert gorgias.main(domain="", email="a@b.com", GORGIAS_API_KEY="key")["output"]["error"]["message"] == "Missing required domain"
    assert gorgias.main(domain="test", email="", GORGIAS_API_KEY="key")["output"]["error"]["message"] == "Missing required email"
    assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="", dry_run=False)["output"]["error"] == "Missing GORGIAS_API_KEY"
def test_invalid_operation(): assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="unknown")["output"]["error"]["message"] == "Unsupported operation"
def test_get_ticket_requires_id(): assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="get_ticket")["output"]["error"]["message"] == "Missing required ticket_id"
def test_update_ticket_requires_id(): assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="update_ticket")["output"]["error"]["message"] == "Missing required ticket_id"
def test_create_ticket_requires_fields():
    assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="create_ticket", message="msg", customer_email="c@d.com")["output"]["error"]["message"] == "Missing required subject"
    assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="create_ticket", subject="hi", customer_email="c@d.com")["output"]["error"]["message"] == "Missing required message"
    assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="create_ticket", subject="hi", message="msg")["output"]["error"]["message"] == "Missing required customer_email"
def test_dry_run():
    result = gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="list_tickets", dry_run=True)
    assert result["output"]["preview"]["url"] == "https://test.gorgias.com/api/tickets"
def test_list_tickets_success():
    client = FakeClient(response=DummyResponse(200, {"data": [{"id": 1}]}))
    result = gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", dry_run=False, client=client)
    assert "data" in result["output"]
def test_create_ticket_success():
    client = FakeClient(response=DummyResponse(201, {"id": 123}))
    result = gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="create_ticket", subject="Test", message="Help", customer_email="c@d.com", dry_run=False, client=client)
    assert result["output"]["id"] == 123
def test_update_ticket_success():
    client = FakeClient(response=DummyResponse(200, {"id": 456}))
    result = gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", operation="update_ticket", ticket_id=456, subject="Updated", dry_run=False, client=client)
    assert result["output"]["id"] == 456
def test_request_exception():
    client = FakeClient(exc=requests.RequestException("Error"))
    assert "Gorgias request failed" in gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", dry_run=False, client=client)["output"]["error"]
def test_invalid_json():
    client = FakeClient(response=DummyResponse(200, ValueError("Bad")))
    assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", dry_run=False, client=client)["output"]["error"] == "Invalid JSON response"
def test_api_error():
    client = FakeClient(response=DummyResponse(401, {"message": "Unauthorized"}))
    assert gorgias.main(domain="test", email="a@b.com", GORGIAS_API_KEY="key", dry_run=False, client=client)["output"]["error"] == "Unauthorized"
