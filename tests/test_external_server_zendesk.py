import requests

from reference_templates.servers.definitions import zendesk


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text
        self.ok = status_code < 400

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class FakeClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls = []

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


def test_missing_required_fields():
    missing_subdomain = zendesk.main(subdomain="", email="agent@example.com", ZENDESK_API_TOKEN="token")
    missing_email = zendesk.main(subdomain="example", email="", ZENDESK_API_TOKEN="token")

    assert missing_subdomain["output"]["error"]["message"] == "Missing required subdomain"
    assert missing_email["output"]["error"]["message"] == "Missing required email"


def test_missing_token_returns_auth_error():
    result = zendesk.main(subdomain="example", email="agent@example.com", ZENDESK_API_TOKEN="", dry_run=False)

    assert result["output"]["error"] == "Missing ZENDESK_API_TOKEN"
    assert result["output"]["status_code"] == 401


def test_invalid_operation_returns_validation_error():
    result = zendesk.main(subdomain="example", email="agent@example.com", ZENDESK_API_TOKEN="token", operation="unknown")

    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_create_ticket_requires_subject_and_comment():
    missing_subject = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        operation="create_ticket",
        subject="",
        comment="Need help",
    )
    missing_comment = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        operation="create_ticket",
        subject="Login issue",
        comment="",
    )

    assert missing_subject["output"]["error"]["message"] == "Missing required subject"
    assert missing_comment["output"]["error"]["message"] == "Missing required comment"


def test_get_ticket_requires_ticket_id():
    result = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        operation="get_ticket",
    )

    assert result["output"]["error"]["message"] == "Missing required ticket_id"


def test_dry_run_returns_preview_for_create():
    result = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        operation="create_ticket",
        subject="Login issue",
        comment="Cannot log in",
        tags=["auth", "high-priority"],
    )

    preview = result["output"]["preview"]
    assert preview["method"] == "POST"
    assert preview["operation"] == "create_ticket"
    assert preview["payload"]["ticket"]["tags"] == ["auth", "high-priority"]


def test_request_exception_returns_error():
    client = FakeClient(exc=requests.RequestException("boom"))

    result = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Zendesk request failed"


def test_invalid_json_response_returns_error():
    response = DummyResponse(status_code=502, json_data=ValueError("no json"), text="bad json")
    client = FakeClient(response=response)

    result = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Invalid JSON response"
    assert result["output"]["status_code"] == 502


def test_api_error_propagates_message_and_status():
    response = DummyResponse(status_code=404, json_data={"error": "Not Found"})
    client = FakeClient(response=response)

    result = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result["output"]["error"] == "Not Found"
    assert result["output"]["status_code"] == 404
    assert result["output"]["response"] == {"error": "Not Found"}


def test_success_returns_payload():
    payload = {"ticket": {"id": 1, "subject": "Hello"}}
    response = DummyResponse(status_code=200, json_data=payload)
    client = FakeClient(response=response)

    result = zendesk.main(
        subdomain="example",
        email="agent@example.com",
        ZENDESK_API_TOKEN="token",
        dry_run=False,
        client=client,
    )

    assert result == {"output": payload}
    method, url, _ = client.calls[0]
    assert method == "GET"
    assert url.endswith("/tickets.json")
