import requests
from reference_templates.servers.definitions import servicenow

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
    assert servicenow.main(instance="", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass")["output"]["error"]["message"] == "Missing required instance"
    assert servicenow.main(instance="dev", table="", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass")["output"]["error"]["message"] == "Missing required table"
    assert servicenow.main(instance="dev", SERVICENOW_USERNAME="", SERVICENOW_PASSWORD="pass")["output"]["error"]["message"] == "Missing required SERVICENOW_USERNAME"
    assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="", dry_run=False)["output"]["error"] == "Missing SERVICENOW_PASSWORD"
def test_invalid_operation(): assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="unknown")["output"]["error"]["message"] == "Unsupported operation"
def test_get_record_requires_id(): assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="get_record")["output"]["error"]["message"] == "Missing required sys_id"
def test_update_record_requires_id(): assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="update_record")["output"]["error"]["message"] == "Missing required sys_id"
def test_create_record_requires_description(): assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="create_record", short_description="")["output"]["error"]["message"] == "Missing required short_description"
def test_dry_run():
    result = servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", dry_run=True)
    assert result["output"]["preview"]["url"] == "https://dev.service-now.com/api/now/table/incident"
    assert result["output"]["preview"]["table"] == "incident"
def test_list_records_success():
    client = FakeClient(response=DummyResponse(200, {"result": [{"sys_id": "1"}]}))
    result = servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", dry_run=False, client=client)
    assert "result" in result["output"]
def test_get_record_success():
    client = FakeClient(response=DummyResponse(200, {"result": {"sys_id": "123"}}))
    result = servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="get_record", sys_id="123", dry_run=False, client=client)
    assert result["output"]["result"]["sys_id"] == "123"
def test_create_record_success():
    client = FakeClient(response=DummyResponse(201, {"result": {"sys_id": "456", "short_description": "New incident"}}))
    result = servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="create_record", short_description="New incident", dry_run=False, client=client)
    assert result["output"]["result"]["sys_id"] == "456"
def test_update_record_success():
    client = FakeClient(response=DummyResponse(200, {"result": {"sys_id": "789"}}))
    result = servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", operation="update_record", sys_id="789", short_description="Updated", dry_run=False, client=client)
    assert result["output"]["result"]["sys_id"] == "789"
def test_request_exception():
    client = FakeClient(exc=requests.RequestException("Error"))
    assert "ServiceNow request failed" in servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", dry_run=False, client=client)["output"]["error"]
def test_invalid_json():
    client = FakeClient(response=DummyResponse(200, ValueError("Bad")))
    assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", dry_run=False, client=client)["output"]["error"] == "Invalid JSON response"
def test_api_error():
    client = FakeClient(response=DummyResponse(401, {"error": "Unauthorized"}))
    assert servicenow.main(instance="dev", SERVICENOW_USERNAME="user", SERVICENOW_PASSWORD="pass", dry_run=False, client=client)["output"]["error"] == "Unauthorized"
