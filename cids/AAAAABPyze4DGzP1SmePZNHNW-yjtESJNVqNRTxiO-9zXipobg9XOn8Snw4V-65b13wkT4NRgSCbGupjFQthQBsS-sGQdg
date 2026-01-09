# ruff: noqa: F821, F706
"""Call the Hunter.io API for email finding and verification."""

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    FormField,
    HttpClientConfig,
    OperationDefinition,
    RequiredField,
    execute_json_request,
    generate_form,
    missing_secret_error,
    validate_and_build_payload,
    validation_error,
)

API_BASE_URL = "https://api.hunter.io/v2"
DOCUMENTATION_URL = "https://hunter.io/api-documentation"

_OPERATIONS = {
    "domain_search": OperationDefinition(
        required=(RequiredField("domain", message="domain is required"),),
    ),
    "email_finder": OperationDefinition(
        required=(
            RequiredField(
                "domain",
                message="domain, first_name, and last_name are required for email_finder",
            ),
            RequiredField(
                "first_name",
                message="domain, first_name, and last_name are required for email_finder",
            ),
            RequiredField(
                "last_name",
                message="domain, first_name, and last_name are required for email_finder",
            ),
        )
    ),
    "email_verifier": OperationDefinition(
        required=(RequiredField("email", message="email is required"),),
    ),
    "email_count": OperationDefinition(
        required=(RequiredField("domain", message="domain is required"),),
    ),
}

_ENDPOINTS = {
    "domain_search": "domain-search",
    "email_finder": "email-finder",
    "email_verifier": "email-verifier",
    "email_count": "email-count",
}

_PARAMETER_BUILDERS = {
    "domain_search": lambda domain, **_: {"domain": domain},
    "email_finder": lambda domain, first_name, last_name, **_: {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
    },
    "email_verifier": lambda email, **_: {"email": email},
    "email_count": lambda domain, **_: {"domain": domain},
}


def _build_preview(
    *,
    operation: str,
    domain: str,
    first_name: str,
    last_name: str,
    email: str,
) -> Dict[str, Any]:
    preview = {
        "operation": operation,
        "api_endpoint": API_BASE_URL,
        "dry_run": True,
    }
    if domain:
        preview["domain"] = domain
    if first_name:
        preview["first_name"] = first_name
    if last_name:
        preview["last_name"] = last_name
    if email:
        preview["email"] = email
    return preview


def main(operation: str = "", domain: str = "", first_name: str = "", last_name: str = "",
         email: str = "", timeout: int = 60, dry_run: bool = True, *, HUNTER_API_KEY: str,
         context=None, client: Optional[ExternalApiClient] = None):
    if not HUNTER_API_KEY:
        return missing_secret_error("HUNTER_API_KEY")

    if not operation:
        return generate_form("hunter", "Hunter.io API",
            "Find and verify email addresses with Hunter.io API.",
            [FormField(name="operation", label="Operation", field_type="select",
                      options=["domain_search", "email_finder", "email_verifier", "email_count"], required=True),
             FormField(name="domain", label="Domain", placeholder="example.com"),
             FormField(name="first_name", label="First Name", placeholder="John"),
             FormField(name="last_name", label="Last Name", placeholder="Doe"),
             FormField(name="email", label="Email", placeholder="john@example.com"),
             FormField(name="dry_run", label="Dry Run", field_type="select",
                      options=["true", "false"], default="true")],
            examples=[{"title": "Domain Search", "code": 'operation=domain_search&domain=example.com'}],
            documentation_url=DOCUMENTATION_URL)

    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        domain=domain,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    endpoint = _ENDPOINTS[operation]
    url = f"{API_BASE_URL}/{endpoint}"
    params = _PARAMETER_BUILDERS[operation](
        domain=domain,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    params["api_key"] = HUNTER_API_KEY

    if dry_run:
        preview = _build_preview(
            operation=operation,
            domain=domain,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        return {"output": preview, "content_type": "application/json"}

    if client is None:
        client = ExternalApiClient(HttpClientConfig(timeout=timeout))

    headers = {"Content-Type": "application/json"}

    return execute_json_request(
        client,
        "GET",
        url,
        headers=headers,
        params=params,
        timeout=timeout,
        request_error_message="Hunter API request failed",
    )
