"""Tests for shared external API utilities."""

from server_utils.external_api import (
    api_error,
    error_output,
    error_response,
    missing_secret_error,
    validation_error,
)


def test_error_output_includes_optional_fields():
    result = error_output(
        "Something went wrong",
        status_code=503,
        response={"detail": "upstream"},
        details="timeout",
    )

    assert result == {
        "output": {
            "error": "Something went wrong",
            "status_code": 503,
            "response": {"detail": "upstream"},
            "details": "timeout",
        }
    }


def test_error_output_omits_missing_optional_fields():
    result = error_output("basic error")

    assert result == {"output": {"error": "basic error"}}


def test_error_response_includes_type_and_content_type():
    result = error_response("boom", error_type="api_error", status_code=500)

    assert result["output"]["error"] == {
        "message": "boom",
        "type": "api_error",
        "status_code": 500,
    }
    assert result["content_type"] == "application/json"


def test_missing_secret_error_marks_auth():
    result = missing_secret_error("TOKEN")

    assert result["output"]["error"]["type"] == "auth_error"
    assert result["output"]["error"]["details"] == {"secret_name": "TOKEN"}


def test_validation_and_api_error_helpers_include_details():
    validation = validation_error("bad", field="name")
    api = api_error("oops", status_code=429, response_body="text")

    assert validation["output"]["error"]["details"] == {"field": "name"}
    assert api["output"]["error"]["status_code"] == 429
