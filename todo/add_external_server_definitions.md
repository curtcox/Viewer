# Add External Server Definitions

Note: Any entries labeled `Planned:` are intentionally future-dated and represent roadmap work, not completed changes.

## Overview

This document outlines the plan for adding server definitions for 100+ external services to the Viewer application. These server definitions will be added to both the default and read-only boot images, enabling users to integrate with popular third-party APIs.

Each external service requires:
1. A Python definition file in `reference_templates/servers/definitions/`
2. A JSON template file in `reference_templates/servers/templates/`
3. An entry in both `default.boot.source.json` and `readonly.boot.source.json`
4. Unit tests, integration tests, and optionally gauge specs

---

## Progress Notes (2025-05-05)

- Hardened Slack and Airtable error handling to include status codes, user-facing hints, and raw response content when JSON parsing fails.
- Kept dry-run defaults intact while tightening validation messages for missing credentials or parameters.

## Progress Notes (2025-12-29)

- Added initial Foundation phase coverage with new Slack and Airtable server definitions plus matching templates.
- Registered both servers in the default and read-only boot source files so they are enabled by default.
- Defaulted both implementations to `dry_run=True` to avoid unintended external calls while shared abstractions and tests are still pending.
- Normalized Slack and Airtable error handling to return JSON objects with an `error` key for clearer downstream rendering.

## Progress Notes (2025-12-30)

- **Phase 1 Foundation Servers COMPLETED**: Added remaining foundation servers (HubSpot, Mailchimp, Zoom) to complete Phase 1.
- HubSpot server tests OAuth authentication with Bearer token for CRM operations (contacts, companies).
- Mailchimp server demonstrates API key extraction from URL format (key-datacenter) and Basic Auth.
- Zoom server validates OAuth flows for meeting and user management operations.
- All 10 Phase 1 foundation servers now implemented with comprehensive test coverage (101 tests passing).
- Ready to proceed to Phase 2: Google Suite servers (9 servers).

## Progress Notes (2025-12-31)

- **Phase 2 Google Suite Servers COMPLETED**: All 9 Google Suite servers implemented.
- Implemented google_drive: List files, upload, download, delete, share (14 tests passing).
- Implemented google_calendar: List/create/update/delete events (13 tests passing).
- Implemented youtube: Search videos, list channels, get comments (12 tests passing).
- Implemented google_contacts: List/create/update/delete contacts (13 tests passing).
- Implemented google_docs: Get/create documents, batch updates (9 tests passing).
- Implemented google_forms: Create forms, get responses (8 tests passing).
- Implemented google_analytics: Run reports, realtime reports, metadata (6 tests passing).
- Implemented google_ads: List campaigns, search with GAQL (8 tests passing).
- All servers follow shared abstraction patterns with GoogleAuthManager and ExternalApiClient.
- Each server includes comprehensive unit tests and dry-run preview functionality.
- Servers registered in both default and readonly boot images.
- Total Phase 2 tests: 81 tests passing (including 10 pre-existing google_sheets tests).
- Ready to proceed to Phase 3: Microsoft Suite servers (5 servers).

---

## Roadmap / Planned Work

## Planned: 2026-02-06

- Added regression tests for Slack and Airtable definitions covering dry-run previews, missing credentials, and API error propagation.
- Confirmed Slack and Airtable return structured `error` payloads and preserve successful API responses unchanged.
- Flagged follow-up work to consolidate shared error helpers before expanding to additional external servers.

## Planned: 2026-02-07

- Propagated HTTP status codes when request exceptions include a response for Slack and Airtable servers.
- Added regression coverage for request exception handling and invalid JSON responses to guard structured error formatting.
- Maintained dry-run behavior while improving troubleshooting details for future shared helper extraction.

## Planned: 2026-02-08

- Extracted a shared `error_output` helper under `server_utils.external_api` and refactored Slack and Airtable to use it.
- Added unit coverage for the shared helper to document the expected payload shape for future servers.

## Planned: 2026-02-09

- Added a shared `ExternalApiClient` with retry, timeout, and safe logging defaults for external API calls.
- Documented request/response logging expectations and timeout overrides with unit coverage to guide future servers.

## Planned: 2026-02-10

- Adopted the shared `ExternalApiClient` in the Slack and Airtable server definitions with optional client injection for testing.
- Updated the Slack and Airtable regression tests to exercise the shared client path while preserving dry-run previews.
- Kept future servers unblocked by keeping request/response shapes unchanged and leaving the shared client configurable per call.

## Planned: 2026-02-11

- Implemented additional shared helpers (`oauth_manager`, `secret_validator`, `form_generator`, `webhook_receiver`) with unit coverage to support upcoming external servers.
- Expanded error formatting utilities with typed helpers for validation, authentication, and API failures while retaining the existing `error_output` payload shape.
- Exported the new utilities via `server_utils.external_api.__init__` for reuse across server definitions and documentation generation.

## Planned: 2026-02-12

- Added Google and Microsoft authentication helpers to support service account and Azure AD client credential flows.
- Validated happy-path token exchanges plus validation and JSON error handling with unit tests.
- Kept the shared external API package exports updated for upcoming server integrations.

## Planned: 2026-02-13

- Tightened Google and Microsoft auth helpers to validate required scopes and return structured errors for token request failures.
- Added stubbed coverage for request exceptions and missing-scope validation to guard future integrations.
- Confirmed helper APIs remain unchanged for downstream server work.

## Planned: 2026-02-14

- Added Google OAuth refresh helper with required parameter validation and structured error handling for failed responses.
- Expanded Google auth tests to cover OAuth refresh happy path, validation errors, request exceptions, and malformed payloads.
- Kept shared client usage consistent to simplify adoption by upcoming Google-backed server definitions.

## Planned: 2026-02-15

- Added optional subject support for Google service account assertions to enable domain-wide delegation use cases.
- Allowed overriding the Google token URI to support regional endpoints or future emulator scenarios while retaining validation for required inputs.
- Expanded Google auth tests for subject handling, custom token URIs, and empty subject validation.

## Planned: 2026-02-16

- Added a Google Sheets server definition that supports reading ranges or appending rows with dry-run previews and shared error handling.
- Reused the shared `ExternalApiClient` and `GoogleAuthManager` for credential validation, with coverage for access token and service account flows.
- Registered the new server in boot sources and templates and added regression tests for validation, API errors, and JSON parsing.

## Planned: 2026-02-17

- Implemented a GitHub server definition supporting listing issues, fetching a single issue, and creating issues using shared HTTP/error helpers.
- Added a GitHub server template and enabled the server in boot sources for default and read-only images.
- Created regression tests covering validation, dry-run previews, API failures, and successful responses for GitHub operations.

## Planned: 2026-02-18

- Added a Notion server definition covering search, page retrieval, and page creation with shared client/error helpers and dry-run previews.
- Registered the Notion server in boot sources and templates so it is enabled by default in default and read-only images.
- Added regression tests for Notion validation, request failures, JSON parsing errors, and successful responses, and noted future expansion for database queries and property mapping.

## Planned: 2026-02-19

- Added a Zendesk server definition for listing tickets, fetching a ticket, and creating tickets with shared HTTP/error helpers, validation, and dry-run previews.
- Registered the Zendesk server template and enabled it across boot sources so it ships by default.
- Added regression tests covering validation, dry-run previews, request failures, JSON parsing errors, and successful Zendesk responses.

## Planned: 2026-02-20

- Added a Stripe server definition covering customer and charge operations plus webhook validation using shared HTTP, validation, and webhook helpers.
- Enabled the Stripe server across boot sources and template registry with dry-run previews for API calls and webhooks.
- Added regression tests for Stripe validation, request failures, JSON parsing errors, API error propagation, webhook signature validation, and successful responses.

## Planned: 2026-02-21

- Added an Asana server definition covering project listing, task listing, task retrieval, and task creation with shared client/error helpers and dry-run previews.
- Registered the Asana server in boot sources and template registry so it is enabled by default.
- Added regression tests for Asana validation, request failures, JSON parsing errors, API error propagation, and successful responses.

---

## Resolved Design Decisions

All open questions have been resolved. The following decisions guide the implementation:

| # | Question | Decision |
|---|----------|----------|
| 1 | OAuth Token Management | Shared OAuth token manager for consistency |
| 2 | Service Account vs User Auth | Support both, with service account as default for Google services |
| 3 | Database Connections | Direct connections for base servers; separate servers for SQLAlchemy, pymongo, and other pooling options |
| 4 | Webhook Endpoints | Include in main server by default; only create separate webhook server if it would require a large increase in complexity of the main server |
| 5 | Server Naming Convention | Use underscores (e.g., `google_sheets`) |
| 6 | Default Endpoints | Show helpful form/documentation by default, require API key for actual calls |
| 7 | Error Message Format | Return JSON with `error` key; server framework renders appropriately |
| 8 | Batch Operations | Support where the API provides them, with separate parameters |
| 9 | Secret Naming Convention | Use the term the service uses (e.g., `STRIPE_API_KEY`, `GOOGLE_ACCESS_TOKEN`) |
| 10 | Read-Only Boot Image | Include all servers; document which operations are read vs write |
| 11 | Secret Validation | Validate where possible, otherwise fail fast on first API call |
| 12 | Mock vs Real API Tests | Mock for CI/CD; option for real tests with API keys in environment |
| 13 | Test API Accounts | Document sandbox setup for each service; use in integration tests |
| 14 | Coverage Requirements | 80% line coverage minimum; 100% for core functionality (authentication, request building) |
| 15 | Rate Limit Handling | Configurable retry with exponential backoff, max 3 retries |
| 16 | Timeout Configuration | Default 60s timeout, configurable via parameter |
| 17 | Logging | Log request URL, method, response status (never log secrets or sensitive data) |
| 18 | Shared Abstractions Location | New top-level package: `server_utils/external_api/` |
| 19 | OAuth Token Persistence | Return refreshed tokens to caller (caller handles persistence) |
| 20 | Database Query Timeout | Separate query timeout from connection timeout for database servers |
| 21 | Pooling Server Configuration | Generic connection string (not separate secrets per database type) |

## Future Changes

- Expand shared helpers (error formatting, HTTP client, secret validation) as additional servers come online.
- Extend shared HTTP client usage to upcoming servers now that Slack and Airtable are migrated; adjust retry/backoff defaults if production usage reveals new needs.
- Generate updated `boot.json`, `default.boot.json`, and `readonly.boot.json` (plus `.cid` files) once CID generation is available so Slack and Airtable appear in the compiled boot images.
- Add integration-style smoke tests for Slack and Airtable using recorded fixtures to verify request shapes against real APIs.
- Extend Airtable coverage to update/delete operations after the shared HTTP client lands, including rate-limit backoff.
- Add unit and integration tests for the new servers, along with form/documentation updates to guide sandbox setup and non-dry-run calls.
- Revisit error payload shapes once the shared `error_response` helper lands to ensure Slack and Airtable match the common schema (status codes, details, retry hints).
- Replace the ad-hoc `error` helpers in Slack and Airtable once the shared error formatting module is available to avoid duplication.
- Evaluate whether the shared HTTP client should support per-call instrumentation hooks (e.g., trace IDs) before scaling to additional servers.
- Expand the GitHub server to cover pagination, issue updates, and comments once initial usage feedback is collected.
- Expand the Notion server to support database query filters, pagination, and richer property mapping once initial usage is stable.
- Expand the Zendesk server to support ticket updates, comments, and pagination once initial usage feedback is collected.
- Expand the Stripe server to include payment intent flows, invoice operations, and Stripe's timestamped webhook signature tolerance when real payloads are available.
- Consider caching OAuth refresh results and normalizing scope handling for Google helpers to reduce redundant calls in future integrations.
- Add support for Google service account ID token flows for services that require targeted `target_audience` assertions.
- Expand the Asana server to support project creation, task updates, and pagination once initial usage feedback is gathered.

 - Expand the Google Sheets server to cover batch updates, value render options, and documentation for token scope selection once initial adoption feedback is collected.

---

## Shared Abstractions

Based on the design decisions, the following shared abstractions will be created before implementing individual servers. These provide consistent behavior across all external service servers.

### Location

All shared abstractions will be in a new top-level package: `server_utils/external_api/`

This is separate from `server_execution/` to maintain clear separation of concerns.

### Module Structure

```
server_utils/
└── external_api/
    ├── __init__.py           # Public API exports
    ├── http_client.py        # HTTP client with retry, timeout, logging
    ├── oauth_manager.py      # OAuth token management
    ├── google_auth.py        # Google-specific auth (service account + OAuth)
    ├── microsoft_auth.py     # Microsoft Graph auth
    ├── error_response.py     # Consistent JSON error formatting
    ├── form_generator.py     # Generate helpful forms for servers
    ├── secret_validator.py   # Validate secrets before API calls
    ├── api_logger.py         # Safe logging (no secrets)
    └── webhook_receiver.py   # Generic webhook receiver
```

### 1. HTTP Client (`http_client.py`)

Provides consistent HTTP behavior for all external API calls.

```python
"""HTTP client with retry, timeout, and logging for external APIs."""

import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class HttpClientConfig:
    """Configuration for HTTP client."""
    timeout: int = 60
    max_retries: int = 3
    backoff_factor: float = 2.0  # Exponential backoff: 2s, 4s, 8s
    retry_on_status: tuple = (429, 500, 502, 503, 504)


class ExternalApiClient:
    """HTTP client with retry, timeout, and safe logging."""

    def __init__(self, config: Optional[HttpClientConfig] = None):
        self.config = config or HttpClientConfig()
        self.session = self._create_session()
        self.logger = logging.getLogger("external_api")

    def _create_session(self) -> requests.Session:
        """Create session with retry configuration."""
        session = requests.Session()
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=self.config.retry_on_status,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Make HTTP request with retry and logging."""
        timeout = timeout or self.config.timeout

        # Log request (no secrets)
        self._log_request(method, url)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                data=data,
                params=params,
                timeout=timeout,
            )

            # Log response (no body)
            self._log_response(method, url, response.status_code)

            return response

        except requests.exceptions.RequestException as e:
            self._log_error(method, url, str(e))
            raise

    def _log_request(self, method: str, url: str) -> None:
        """Log request without sensitive data."""
        self.logger.info(f"API Request: {method} {url}")

    def _log_response(self, method: str, url: str, status: int) -> None:
        """Log response status."""
        self.logger.info(f"API Response: {method} {url} -> {status}")

    def _log_error(self, method: str, url: str, error: str) -> None:
        """Log error without sensitive data."""
        self.logger.error(f"API Error: {method} {url} -> {error}")

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        return self.request("PATCH", url, **kwargs)
```

### 2. OAuth Manager (`oauth_manager.py`)

Shared OAuth token management with refresh capability. Returns refreshed tokens to the caller (caller is responsible for persistence).

```python
"""OAuth token manager for external APIs."""

import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import requests


@dataclass
class OAuthTokens:
    """OAuth token container."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    token_type: str = "Bearer"

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired or will expire soon."""
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - buffer_seconds)


class OAuthManager:
    """Manages OAuth tokens with automatic refresh.

    Note: This class returns refreshed tokens to the caller. The caller is
    responsible for persisting tokens if needed (e.g., updating secrets store).
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: Optional[list] = None,
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []
        self._tokens: Optional[OAuthTokens] = None

    def get_access_token(self, refresh_token: Optional[str] = None) -> Tuple[str, Optional[OAuthTokens]]:
        """Get valid access token, refreshing if needed.

        Returns:
            Tuple of (access_token, new_tokens_if_refreshed).
            If tokens were refreshed, caller should persist new_tokens.
        """
        if self._tokens and not self._tokens.is_expired():
            return self._tokens.access_token, None

        if refresh_token or (self._tokens and self._tokens.refresh_token):
            return self._refresh_token(refresh_token or self._tokens.refresh_token)

        raise ValueError("No valid token available and no refresh token provided")

    def _refresh_token(self, refresh_token: str) -> Tuple[str, OAuthTokens]:
        """Refresh the access token.

        Returns:
            Tuple of (access_token, new_tokens). Caller should persist new_tokens.
        """
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        self._tokens = OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=time.time() + data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
        )

        return self._tokens.access_token, self._tokens

    def set_tokens(self, tokens: OAuthTokens) -> None:
        """Set tokens directly (e.g., from stored secrets)."""
        self._tokens = tokens

    def get_auth_header(self, refresh_token: Optional[str] = None) -> Tuple[Dict[str, str], Optional[OAuthTokens]]:
        """Get Authorization header with valid token.

        Returns:
            Tuple of (headers_dict, new_tokens_if_refreshed).
        """
        token, new_tokens = self.get_access_token(refresh_token)
        token_type = self._tokens.token_type if self._tokens else "Bearer"
        return {"Authorization": f"{token_type} {token}"}, new_tokens
```

### 3. Google Auth (`google_auth.py`)

Google-specific authentication supporting both service accounts and OAuth.

```python
"""Google authentication for service accounts and OAuth."""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request


@dataclass
class GoogleAuthConfig:
    """Google authentication configuration."""
    # For service account auth
    service_account_json: Optional[str] = None
    # For OAuth auth
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    # Common
    scopes: Optional[list] = None


class GoogleAuthManager:
    """Manages Google authentication."""

    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, config: GoogleAuthConfig):
        self.config = config
        self._credentials = None

    def get_auth_header(self) -> Dict[str, str]:
        """Get Authorization header for Google API calls."""
        if self.config.service_account_json:
            return self._get_service_account_header()
        elif self.config.access_token:
            return self._get_oauth_header()
        else:
            raise ValueError("No authentication configured")

    def _get_service_account_header(self) -> Dict[str, str]:
        """Get header using service account credentials."""
        if self._credentials is None:
            info = json.loads(self.config.service_account_json)
            self._credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=self.config.scopes or [],
            )

        if self._credentials.expired:
            self._credentials.refresh(Request())

        return {"Authorization": f"Bearer {self._credentials.token}"}

    def _get_oauth_header(self) -> Dict[str, str]:
        """Get header using OAuth tokens."""
        # If we have refresh capability, use it
        if self.config.refresh_token and self.config.client_id:
            # Implement token refresh if needed
            pass

        return {"Authorization": f"Bearer {self.config.access_token}"}

    @property
    def auth_type(self) -> str:
        """Return the authentication type being used."""
        if self.config.service_account_json:
            return "service_account"
        return "oauth"
```

### 4. Error Response (`error_response.py`)

Consistent JSON error formatting.

```python
"""Consistent error response formatting."""

from typing import Dict, Any, Optional


def error_response(
    message: str,
    error_type: str = "api_error",
    status_code: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a consistent error response.

    Args:
        message: Human-readable error message
        error_type: Error category (e.g., "auth_error", "api_error", "validation_error")
        status_code: HTTP status code if applicable
        details: Additional error details

    Returns:
        Dict with 'error' key containing error information
    """
    error = {
        "error": {
            "message": message,
            "type": error_type,
        }
    }

    if status_code is not None:
        error["error"]["status_code"] = status_code

    if details:
        error["error"]["details"] = details

    return {"output": error, "content_type": "application/json"}


def missing_secret_error(secret_name: str) -> Dict[str, Any]:
    """Error response for missing API secret."""
    return error_response(
        message=f"Missing required secret: {secret_name}",
        error_type="auth_error",
        details={"secret_name": secret_name},
    )


def api_error(
    message: str,
    status_code: Optional[int] = None,
    response_body: Optional[str] = None,
) -> Dict[str, Any]:
    """Error response for API call failure."""
    details = {}
    if response_body:
        details["response"] = response_body[:500]  # Truncate long responses

    return error_response(
        message=message,
        error_type="api_error",
        status_code=status_code,
        details=details if details else None,
    )


def validation_error(message: str, field: Optional[str] = None) -> Dict[str, Any]:
    """Error response for validation failure."""
    details = {"field": field} if field else None
    return error_response(
        message=message,
        error_type="validation_error",
        details=details,
    )
```

### 5. Form Generator (`form_generator.py`)

Generate helpful HTML forms for server documentation.

```python
"""Generate HTML forms for external API servers."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from html import escape


@dataclass
class FormField:
    """Form field definition."""
    name: str
    label: str
    field_type: str = "text"  # text, textarea, select, hidden
    default: str = ""
    required: bool = False
    options: Optional[List[str]] = None  # For select fields
    placeholder: str = ""
    help_text: str = ""


def generate_form(
    server_name: str,
    title: str,
    description: str,
    fields: List[FormField],
    endpoint: str = "",
    examples: Optional[List[Dict[str, str]]] = None,
    documentation_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an HTML form for an API server.

    Args:
        server_name: Server identifier
        title: Human-readable title
        description: Server description
        fields: List of form fields
        endpoint: Form action endpoint
        examples: Example API calls
        documentation_url: Link to API documentation

    Returns:
        Dict with 'output' containing HTML form
    """
    action = endpoint or f"/{server_name}"

    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>{escape(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; max-width: 800px; }}
        h1 {{ color: #333; }}
        .description {{ color: #666; margin-bottom: 20px; }}
        .field {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; }}
        input[type="text"], textarea, select {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        textarea {{ height: 100px; font-family: monospace; }}
        .help {{ font-size: 12px; color: #666; margin-top: 3px; }}
        .required {{ color: red; }}
        button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #0056b3; }}
        .examples {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin-top: 20px; }}
        .examples h3 {{ margin-top: 0; }}
        .example {{ margin-bottom: 10px; }}
        code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #e9ecef; padding: 10px; border-radius: 4px; overflow-x: auto; }}
        .doc-link {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>{escape(title)}</h1>
    <p class="description">{escape(description)}</p>

    <form method="post" action="{escape(action)}">
'''

    for field in fields:
        required_mark = '<span class="required">*</span>' if field.required else ''
        html += f'        <div class="field">\n'
        html += f'            <label for="{escape(field.name)}">{escape(field.label)} {required_mark}</label>\n'

        if field.field_type == "textarea":
            html += f'            <textarea name="{escape(field.name)}" id="{escape(field.name)}" placeholder="{escape(field.placeholder)}">{escape(field.default)}</textarea>\n'
        elif field.field_type == "select" and field.options:
            html += f'            <select name="{escape(field.name)}" id="{escape(field.name)}">\n'
            for option in field.options:
                selected = ' selected' if option == field.default else ''
                html += f'                <option value="{escape(option)}"{selected}>{escape(option)}</option>\n'
            html += '            </select>\n'
        elif field.field_type == "hidden":
            html += f'            <input type="hidden" name="{escape(field.name)}" value="{escape(field.default)}">\n'
        else:
            required_attr = ' required' if field.required else ''
            html += f'            <input type="text" name="{escape(field.name)}" id="{escape(field.name)}" value="{escape(field.default)}" placeholder="{escape(field.placeholder)}"{required_attr}>\n'

        if field.help_text:
            html += f'            <div class="help">{escape(field.help_text)}</div>\n'

        html += '        </div>\n'

    html += '''        <button type="submit">Execute</button>
    </form>
'''

    if examples:
        html += '''
    <div class="examples">
        <h3>Examples</h3>
'''
        for example in examples:
            html += f'        <div class="example">\n'
            html += f'            <strong>{escape(example.get("title", "Example"))}:</strong>\n'
            html += f'            <pre>{escape(example.get("code", ""))}</pre>\n'
            html += '        </div>\n'
        html += '    </div>\n'

    if documentation_url:
        html += f'''
    <div class="doc-link">
        <a href="{escape(documentation_url)}" target="_blank">View API Documentation</a>
    </div>
'''

    html += '''</body>
</html>'''

    return {"output": html, "content_type": "text/html"}
```

### 6. Secret Validator (`secret_validator.py`)

Validate secrets before making API calls.

```python
"""Validate API secrets before making calls."""

from typing import Dict, Any, Optional, Callable
import requests


def validate_secret(
    secret_value: str,
    secret_name: str,
    validator: Optional[Callable[[str], bool]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Validate a secret value.

    Args:
        secret_value: The secret value to validate
        secret_name: Name of the secret (for error messages)
        validator: Optional custom validation function

    Returns:
        None if valid, error response dict if invalid
    """
    from .error_response import missing_secret_error, validation_error

    if not secret_value:
        return missing_secret_error(secret_name)

    if validator and not validator(secret_value):
        return validation_error(f"Invalid {secret_name} format")

    return None


def validate_api_key_with_endpoint(
    api_key: str,
    validation_url: str,
    headers_builder: Callable[[str], Dict[str, str]],
    secret_name: str = "API_KEY",
) -> Optional[Dict[str, Any]]:
    """
    Validate an API key by making a test request.

    Args:
        api_key: The API key to validate
        validation_url: URL to call for validation
        headers_builder: Function to build headers with the API key
        secret_name: Name of the secret (for error messages)

    Returns:
        None if valid, error response dict if invalid
    """
    from .error_response import missing_secret_error, api_error

    if not api_key:
        return missing_secret_error(secret_name)

    try:
        headers = headers_builder(api_key)
        response = requests.get(validation_url, headers=headers, timeout=10)

        if response.status_code == 401:
            return api_error(
                message=f"Invalid or expired {secret_name}",
                status_code=401,
            )
        elif response.status_code == 403:
            return api_error(
                message=f"Insufficient permissions for {secret_name}",
                status_code=403,
            )

        return None

    except requests.exceptions.RequestException as e:
        # Can't validate, but don't fail - let the actual request fail
        return None
```

### 7. Webhook Receiver (`webhook_receiver.py`)

Generic webhook receiver for services that support webhooks.

```python
"""Generic webhook receiver for external services."""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import hmac
import hashlib


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    secret: str
    signature_header: str = "X-Signature"
    signature_algorithm: str = "sha256"
    signature_prefix: str = ""  # e.g., "sha256=" for GitHub


class WebhookReceiver:
    """Generic webhook receiver with signature validation."""

    def __init__(self, config: WebhookConfig):
        self.config = config

    def validate_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Validate webhook signature."""
        expected = hmac.new(
            self.config.secret.encode(),
            payload,
            getattr(hashlib, self.config.signature_algorithm),
        ).hexdigest()

        if self.config.signature_prefix:
            expected = f"{self.config.signature_prefix}{expected}"

        return hmac.compare_digest(expected, signature)

    def process_webhook(
        self,
        payload: bytes,
        headers: Dict[str, str],
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Process incoming webhook.

        Args:
            payload: Raw request body
            headers: Request headers
            handler: Function to process the webhook payload

        Returns:
            Response dict
        """
        from .error_response import error_response
        import json

        # Validate signature
        signature = headers.get(self.config.signature_header, "")
        if not self.validate_signature(payload, signature):
            return error_response(
                message="Invalid webhook signature",
                error_type="auth_error",
                status_code=401,
            )

        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            return error_response(
                message=f"Invalid JSON payload: {e}",
                error_type="validation_error",
                status_code=400,
            )

        # Process with handler
        return handler(data)
```

### Shared Abstraction Tests

Each shared module needs comprehensive tests:

| Module | Test File | Key Tests |
|--------|-----------|-----------|
| `http_client.py` | `tests/test_external_api_http_client.py` | Retry behavior, timeout, logging, all HTTP methods |
| `oauth_manager.py` | `tests/test_external_api_oauth.py` | Token refresh, expiry detection, header generation |
| `google_auth.py` | `tests/test_external_api_google_auth.py` | Service account auth, OAuth auth, token refresh |
| `microsoft_auth.py` | `tests/test_external_api_microsoft_auth.py` | Graph API auth, token refresh |
| `error_response.py` | `tests/test_external_api_errors.py` | All error types, JSON structure |
| `form_generator.py` | `tests/test_external_api_forms.py` | Form generation, field types, examples |
| `secret_validator.py` | `tests/test_external_api_secrets.py` | Validation, endpoint validation |
| `webhook_receiver.py` | `tests/test_external_api_webhooks.py` | Signature validation, payload processing |

---

## Service Categories and Inventory

### Category 1: Productivity & Workspace (Google Suite)
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Google Sheets | `google_sheets` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/sheets/api |
| Gmail | `gmail` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/gmail/api |
| Google Drive | `google_drive` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/drive/api |
| Google Calendar | `google_calendar` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/calendar/api |
| Google Forms | `google_forms` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/forms/api |
| Google Contacts | `google_contacts` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/people/api |
| Google Docs | `google_docs` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/docs/api |
| Google Ads | `google_ads` | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID` | https://developers.google.com/google-ads/api |
| Google Analytics 4 | `google_analytics` | `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_ACCESS_TOKEN` | https://developers.google.com/analytics/devguides/reporting |

### Category 2: Productivity & Workspace (Microsoft 365)
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Microsoft 365 Outlook | `microsoft_outlook` | `MICROSOFT_ACCESS_TOKEN` or `MICROSOFT_CLIENT_ID`/`MICROSOFT_CLIENT_SECRET` | https://docs.microsoft.com/en-us/graph/api/resources/mail-api-overview |
| Microsoft Teams | `microsoft_teams` | `MICROSOFT_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/graph/api/resources/teams-api-overview |
| OneDrive | `onedrive` | `MICROSOFT_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/graph/api/resources/onedrive |
| Microsoft Excel | `microsoft_excel` | `MICROSOFT_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/graph/api/resources/excel |
| Microsoft Dynamics 365 | `dynamics365` | `DYNAMICS365_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/dynamics365/customer-engagement/developer/webapi/web-api-reference |

### Category 3: Project Management
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Trello | `trello` | `TRELLO_API_KEY`, `TRELLO_TOKEN` | https://developer.atlassian.com/cloud/trello/rest/ |
| Asana | `asana` | `ASANA_ACCESS_TOKEN` | https://developers.asana.com/docs |
| Monday.com | `monday` | `MONDAY_API_KEY` | https://developer.monday.com/api-reference |
| ClickUp | `clickup` | `CLICKUP_API_KEY` | https://clickup.com/api |
| Jira Cloud | `jira` | `JIRA_API_TOKEN`, `JIRA_EMAIL`, `JIRA_DOMAIN` | https://developer.atlassian.com/cloud/jira/platform/rest/v3/ |
| Confluence | `confluence` | `CONFLUENCE_API_TOKEN`, `CONFLUENCE_EMAIL`, `CONFLUENCE_DOMAIN` | https://developer.atlassian.com/cloud/confluence/rest/v1/ |
| Basecamp | `basecamp` | `BASECAMP_ACCESS_TOKEN` | https://github.com/basecamp/bc3-api |
| Smartsheet | `smartsheet` | `SMARTSHEET_ACCESS_TOKEN` | https://smartsheet-platform.github.io/api-docs/ |
| Todoist | `todoist` | `TODOIST_API_TOKEN` | https://developer.todoist.com/rest/v2/ |

### Category 4: Databases & Productivity Tools
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Airtable | `airtable` | `AIRTABLE_ACCESS_TOKEN` | https://airtable.com/developers/web/api |
| Notion | `notion` | `NOTION_API_KEY` | https://developers.notion.com/ |
| Coda | `coda` | `CODA_API_TOKEN` | https://coda.io/developers/apis/v1 |

### Category 5: Communication & Messaging
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Slack | `slack` | `SLACK_BOT_TOKEN` or `SLACK_USER_TOKEN` | https://api.slack.com/ |
| Discord | `discord` | `DISCORD_BOT_TOKEN` | https://discord.com/developers/docs |
| Twilio | `twilio` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | https://www.twilio.com/docs/usage/api |
| WhatsApp Business | `whatsapp` | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | https://developers.facebook.com/docs/whatsapp |
| Telegram | `telegram` | `TELEGRAM_BOT_TOKEN` | https://core.telegram.org/bots/api |

### Category 6: Video Conferencing & Scheduling
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Zoom | `zoom` | `ZOOM_JWT_TOKEN` or `ZOOM_CLIENT_ID`/`ZOOM_CLIENT_SECRET` | https://marketplace.zoom.us/docs/api-reference |
| Calendly | `calendly` | `CALENDLY_API_KEY` | https://developer.calendly.com/api-docs |

### Category 7: CRM & Sales
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| HubSpot | `hubspot` | `HUBSPOT_ACCESS_TOKEN` | https://developers.hubspot.com/docs/api/overview |
| Salesforce | `salesforce` | `SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_INSTANCE_URL` | https://developer.salesforce.com/docs/apis |
| Pipedrive | `pipedrive` | `PIPEDRIVE_API_TOKEN` | https://developers.pipedrive.com/docs/api/v1 |
| Close CRM | `close_crm` | `CLOSE_API_KEY` | https://developer.close.com/ |
| Zoho CRM | `zoho_crm` | `ZOHO_ACCESS_TOKEN` | https://www.zoho.com/crm/developer/docs/api/v2/ |
| Insightly | `insightly` | `INSIGHTLY_API_KEY` | https://api.insightly.com/v3.1/Help |

### Category 8: Customer Support
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Intercom | `intercom` | `INTERCOM_ACCESS_TOKEN` | https://developers.intercom.com/docs |
| Zendesk | `zendesk` | `ZENDESK_API_TOKEN`, `ZENDESK_EMAIL`, `ZENDESK_SUBDOMAIN` | https://developer.zendesk.com/api-reference |
| Freshdesk | `freshdesk` | `FRESHDESK_API_KEY`, `FRESHDESK_DOMAIN` | https://developers.freshdesk.com/api/ |
| Help Scout | `helpscout` | `HELPSCOUT_API_KEY` | https://developer.helpscout.com/ |
| Front | `front` | `FRONT_API_TOKEN` | https://dev.frontapp.com/reference |
| Gorgias | `gorgias` | `GORGIAS_API_KEY`, `GORGIAS_DOMAIN` | https://developers.gorgias.com/ |
| ServiceNow | `servicenow` | `SERVICENOW_INSTANCE`, `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD` | https://developer.servicenow.com/dev.do |

### Category 9: E-commerce
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Shopify | `shopify` | `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_STORE_URL` | https://shopify.dev/docs/api |
| WooCommerce | `woocommerce` | `WOOCOMMERCE_CONSUMER_KEY`, `WOOCOMMERCE_CONSUMER_SECRET`, `WOOCOMMERCE_STORE_URL` | https://woocommerce.github.io/woocommerce-rest-api-docs/ |
| eBay | `ebay` | `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID` | https://developer.ebay.com/docs |
| Etsy | `etsy` | `ETSY_API_KEY` | https://developers.etsy.com/documentation |

### Category 10: Payment Processing
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Stripe | `stripe` | `STRIPE_API_KEY` | https://stripe.com/docs/api |
| PayPal | `paypal` | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | https://developer.paypal.com/docs/api/overview/ |

### Category 11: Email Marketing
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Mailchimp | `mailchimp` | `MAILCHIMP_API_KEY` | https://mailchimp.com/developer/marketing/api/ |
| Klaviyo | `klaviyo` | `KLAVIYO_API_KEY` | https://developers.klaviyo.com/en/reference/api-overview |
| ActiveCampaign | `activecampaign` | `ACTIVECAMPAIGN_API_KEY`, `ACTIVECAMPAIGN_URL` | https://developers.activecampaign.com/reference |
| MailerLite | `mailerlite` | `MAILERLITE_API_KEY` | https://developers.mailerlite.com/docs |
| SendGrid | `sendgrid` | `SENDGRID_API_KEY` | https://docs.sendgrid.com/api-reference |
| Mailgun | `mailgun` | `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` | https://documentation.mailgun.com/en/latest/api_reference.html |
| Postmark | `postmark` | `POSTMARK_SERVER_TOKEN` | https://postmarkapp.com/developer |

### Category 12: AI & Machine Learning
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| OpenAI (ChatGPT) | `openai_chat` | `OPENAI_API_KEY` | https://platform.openai.com/docs/api-reference (Already exists) |

### Category 13: Document Management & E-Signature
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| DocuSign | `docusign` | `DOCUSIGN_ACCESS_TOKEN`, `DOCUSIGN_ACCOUNT_ID` | https://developers.docusign.com/docs |
| PandaDoc | `pandadoc` | `PANDADOC_API_KEY` | https://developers.pandadoc.com/reference |
| Dropbox | `dropbox` | `DROPBOX_ACCESS_TOKEN` | https://www.dropbox.com/developers/documentation |
| Box | `box` | `BOX_ACCESS_TOKEN` | https://developer.box.com/reference/ |

### Category 14: Developer Tools
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| GitHub | `github` | `GITHUB_TOKEN` | https://docs.github.com/en/rest |
| GitLab | `gitlab` | `GITLAB_ACCESS_TOKEN` | https://docs.gitlab.com/ee/api/ |

### Category 15: Design & Collaboration
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Miro | `miro` | `MIRO_ACCESS_TOKEN` | https://developers.miro.com/reference |
| Figma | `figma` | `FIGMA_ACCESS_TOKEN` | https://www.figma.com/developers/api |

### Category 16: Website Builders
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Webflow | `webflow` | `WEBFLOW_API_TOKEN` | https://developers.webflow.com/ |
| WordPress | `wordpress` | `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD`, `WORDPRESS_SITE_URL` | https://developer.wordpress.org/rest-api/ |
| Wix | `wix` | `WIX_API_KEY` | https://dev.wix.com/api/rest |
| Squarespace | `squarespace` | `SQUARESPACE_API_KEY` | https://developers.squarespace.com/ |

### Category 17: Forms & Surveys
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Typeform | `typeform` | `TYPEFORM_ACCESS_TOKEN` | https://developer.typeform.com/ |
| Jotform | `jotform` | `JOTFORM_API_KEY` | https://api.jotform.com/docs/ |

### Category 18: Advertising
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Meta Ads | `meta_ads` | `META_ACCESS_TOKEN` | https://developers.facebook.com/docs/marketing-apis |
| LinkedIn Ads | `linkedin_ads` | `LINKEDIN_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/linkedin/marketing/ |
| YouTube | `youtube` | `YOUTUBE_API_KEY` | https://developers.google.com/youtube/v3 |

### Category 19: Finance & Accounting
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| QuickBooks Online | `quickbooks` | `QUICKBOOKS_ACCESS_TOKEN`, `QUICKBOOKS_REALM_ID` | https://developer.intuit.com/app/developer/qbo/docs/api |
| Xero | `xero` | `XERO_ACCESS_TOKEN`, `XERO_TENANT_ID` | https://developer.xero.com/documentation/api |
| FreshBooks | `freshbooks` | `FRESHBOOKS_ACCESS_TOKEN` | https://www.freshbooks.com/api |

### Category 20: Data Processing & Utilities
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| CloudConvert | `cloudconvert` | `CLOUDCONVERT_API_KEY` | https://cloudconvert.com/api/v2 |
| PDF.co | `pdfco` | `PDFCO_API_KEY` | https://developer.pdf.co/ |
| Docparser | `docparser` | `DOCPARSER_API_KEY` | https://dev.docparser.com/ |
| Parseur/Mailparser | `parseur` | `PARSEUR_API_KEY` | https://help.parseur.com/en/articles/5154126 |
| Apify | `apify` | `APIFY_API_TOKEN` | https://docs.apify.com/api/v2 |
| Clearbit | `clearbit` | `CLEARBIT_API_KEY` | https://clearbit.com/docs |
| Hunter.io | `hunter` | `HUNTER_API_KEY` | https://hunter.io/api-documentation |
| Bitly | `bitly` | `BITLY_ACCESS_TOKEN` | https://dev.bitly.com/ |
| UptimeRobot | `uptimerobot` | `UPTIMEROBOT_API_KEY` | https://uptimerobot.com/api/ |

### Category 21: Cloud Storage
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| AWS S3 | `aws_s3` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | https://docs.aws.amazon.com/s3/index.html |
| Google Cloud Storage | `gcs` | `GOOGLE_SERVICE_ACCOUNT_JSON` | https://cloud.google.com/storage/docs/reference |
| Azure Blob Storage | `azure_blob` | `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY` | https://docs.microsoft.com/en-us/rest/api/storageservices/ |

### Category 22: Databases (Direct Connection)

Database servers support separate connection timeout and query timeout parameters.

| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| MySQL | `mysql` | `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Direct connection |
| PostgreSQL | `postgresql` | `POSTGRESQL_HOST`, `POSTGRESQL_USER`, `POSTGRESQL_PASSWORD`, `POSTGRESQL_DATABASE` | Direct connection |
| MongoDB | `mongodb` | `MONGODB_URI` | https://www.mongodb.com/docs/drivers/python/ |

**Timeout parameters for database servers:**
- `connection_timeout`: Timeout for establishing connection (default: 10s)
- `query_timeout`: Timeout for query execution (default: 60s)

### Category 22b: Database Connection Pooling (Separate Servers)

Pooling servers accept a generic connection string parameter.

| Service | Server Name | API Key/Secret Name | Notes |
|---------|-------------|---------------------|-------|
| SQLAlchemy Pool | `sqlalchemy_pool` | `DATABASE_URL` | Generic connection string for MySQL/PostgreSQL pooling |
| PyMongo Pool | `pymongo_pool` | `MONGODB_URI` | For MongoDB pooling |

### Category 23: Analytics & Data Warehousing
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Segment | `segment` | `SEGMENT_WRITE_KEY` | https://segment.com/docs/connections/sources/catalog/libraries/server/http-api/ |
| Mixpanel | `mixpanel` | `MIXPANEL_TOKEN`, `MIXPANEL_API_SECRET` | https://developer.mixpanel.com/reference |
| Amplitude | `amplitude` | `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY` | https://developers.amplitude.com/docs/http-api-v2 |
| BigQuery | `bigquery` | `GOOGLE_SERVICE_ACCOUNT_JSON` | https://cloud.google.com/bigquery/docs/reference/rest |
| Snowflake | `snowflake` | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE` | https://docs.snowflake.com/en/developer-guide/sql-api |

---

## Updated Implementation Pattern

### Server Definition Template (Using Shared Abstractions)

Each external service server will use the shared abstractions:

```python
# ruff: noqa: F821, F706
"""Call the {ServiceName} API using automatic main() mapping."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient,
    HttpClientConfig,
    error_response,
    missing_secret_error,
    generate_form,
    FormField,
)


API_BASE_URL = "https://api.example.com/v1"
DOCUMENTATION_URL = "https://example.com/docs"


def main(
    endpoint: str = "",
    method: str = "GET",
    data: Optional[str] = None,
    timeout: int = 60,
    *,
    SERVICE_API_KEY: str,
    context=None,
):
    """
    Make a request to the {ServiceName} API.

    Args:
        endpoint: The API endpoint to call (e.g., "/users", "/messages")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: JSON data for POST/PUT requests
        timeout: Request timeout in seconds (default: 60)
        SERVICE_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)

    Returns:
        Dict with 'output' containing the API response
    """
    # Show form if no endpoint provided
    if not endpoint:
        return generate_form(
            server_name="service_name",
            title="Service Name API",
            description="Make requests to the Service Name API.",
            fields=[
                FormField(name="endpoint", label="Endpoint", placeholder="/users", required=True),
                FormField(name="method", label="Method", field_type="select",
                         options=["GET", "POST", "PUT", "DELETE"], default="GET"),
                FormField(name="data", label="JSON Data", field_type="textarea",
                         placeholder='{"key": "value"}'),
                FormField(name="timeout", label="Timeout (seconds)", default="60"),
            ],
            examples=[
                {"title": "List users", "code": "GET /users"},
                {"title": "Create user", "code": "POST /users\n{\"name\": \"John\"}"},
            ],
            documentation_url=DOCUMENTATION_URL,
        )

    # Validate secret
    if not SERVICE_API_KEY:
        return missing_secret_error("SERVICE_API_KEY")

    # Create client with configured timeout and retry
    config = HttpClientConfig(timeout=timeout)
    client = ExternalApiClient(config)

    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {SERVICE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = client.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=data if data else None,
        )
        response.raise_for_status()
        return {"output": response.json()}

    except Exception as e:
        return error_response.api_error(str(e))
```

### JSON Template Pattern

```json
{
  "id": "service_name",
  "name": "Service Name API",
  "description": "Make requests to the Service Name API.",
  "definition_file": "definitions/service_name.py",
  "documentation_url": "https://example.com/docs",
  "operations": {
    "read": ["GET /users", "GET /items"],
    "write": ["POST /users", "PUT /users/{id}", "DELETE /users/{id}"]
  }
}
```

---

## Test Plan

### Test Categories

#### 1. Shared Abstraction Tests (Must pass before server implementation)

| Test File | Module | Tests |
|-----------|--------|-------|
| `tests/test_external_api_http_client.py` | `http_client.py` | Retry behavior (3 retries), exponential backoff (2s, 4s, 8s), timeout configuration, all HTTP methods, logging without secrets |
| `tests/test_external_api_oauth.py` | `oauth_manager.py` | Token refresh, expiry detection, header generation |
| `tests/test_external_api_google_auth.py` | `google_auth.py` | Service account auth, OAuth auth, auth type detection |
| `tests/test_external_api_microsoft_auth.py` | `microsoft_auth.py` | Graph API auth, token refresh |
| `tests/test_external_api_errors.py` | `error_response.py` | All error types, JSON structure, content_type |
| `tests/test_external_api_forms.py` | `form_generator.py` | Form generation, all field types, examples, documentation links |
| `tests/test_external_api_secrets.py` | `secret_validator.py` | Missing secret, invalid format, endpoint validation |
| `tests/test_external_api_webhooks.py` | `webhook_receiver.py` | Signature validation, payload processing |

#### 2. Unit Tests (per server)
Each server definition needs the following unit tests:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_missing_api_key` | Server returns JSON error when API key is missing |
| `test_{server}_shows_form_without_endpoint` | Server shows helpful form when no endpoint provided |
| `test_{server}_get_request` | Server makes GET request correctly |
| `test_{server}_post_request` | Server makes POST request with data |
| `test_{server}_put_request` | Server makes PUT request with data |
| `test_{server}_delete_request` | Server makes DELETE request |
| `test_{server}_api_error_handling` | Server returns JSON error on API failure |
| `test_{server}_timeout_handling` | Server handles request timeouts |
| `test_{server}_custom_timeout` | Server respects custom timeout parameter |
| `test_{server}_rate_limit_retry` | Server retries on 429 (via shared client) |

#### 3. Integration Tests (per server)

| Test Name | Description |
|-----------|-------------|
| `test_{server}_server_registered_in_boot_image` | Server exists in boot image |
| `test_{server}_accessible_via_url` | Server accessible at expected URL |
| `test_{server}_form_rendering` | Server renders input form when accessed with GET |
| `test_{server}_request_execution` | Server executes request and returns result |
| `test_{server}_chaining_input` | Server accepts chained input from another server |
| `test_{server}_cid_output` | Server output can be stored as CID |

#### 4. Boot Image Tests

| Test Name | Description |
|-----------|-------------|
| `test_all_external_servers_in_default_boot` | All external servers present in default boot |
| `test_all_external_servers_in_readonly_boot` | All external servers present in readonly boot |
| `test_external_servers_enabled_by_default` | All external servers enabled |
| `test_external_server_cids_valid` | All server CIDs are valid |
| `test_external_server_definitions_valid_python` | All server definitions are valid Python |
| `test_no_duplicate_server_names` | No duplicate server names |
| `test_server_names_follow_convention` | Server names use underscores |
| `test_server_templates_document_operations` | Templates document read vs write operations |

---

## Implementation Phases (Revised)

### Phase 0: Shared Infrastructure (REQUIRED FIRST)
Build and test all shared abstractions before implementing any servers:

**Files to create:**
- `server_utils/__init__.py`
- `server_utils/external_api/__init__.py`
- `server_utils/external_api/http_client.py`
- `server_utils/external_api/oauth_manager.py`
- `server_utils/external_api/google_auth.py`
- `server_utils/external_api/microsoft_auth.py`
- `server_utils/external_api/error_response.py`
- `server_utils/external_api/form_generator.py`
- `server_utils/external_api/secret_validator.py`
- `server_utils/external_api/webhook_receiver.py`

**Tests to create:**
- `tests/test_external_api_http_client.py`
- `tests/test_external_api_oauth.py`
- `tests/test_external_api_google_auth.py`
- `tests/test_external_api_microsoft_auth.py`
- `tests/test_external_api_errors.py`
- `tests/test_external_api_forms.py`
- `tests/test_external_api_secrets.py`
- `tests/test_external_api_webhooks.py`

**Acceptance criteria:**
- [ ] All shared modules implemented
- [ ] 100% test coverage for shared modules
- [ ] Documentation for each module

### Phase 1: Foundation Servers (10 servers) ✅ COMPLETE
First servers using shared infrastructure as validation:
- ✅ google_sheets (tests Google auth)
- ✅ slack (tests simple Bearer token)
- ✅ stripe (tests webhook receiver)
- ✅ github (tests simple token auth)
- ✅ airtable (tests Bearer token)
- ✅ notion (tests Bearer token)
- ✅ hubspot (tests OAuth) - Added 2025-12-30
- ✅ mailchimp (tests API key in URL) - Added 2025-12-30
- ✅ openai_chat (already exists - verified integration)
- ✅ zoom (tests OAuth) - Added 2025-12-30

### Phase 2: Google Suite (9 servers) ✅ COMPLETE
- ✅ gmail (already exists)
- ✅ google_sheets (already exists)
- ✅ google_drive - Added 2025-12-31
- ✅ google_calendar - Added 2025-12-31
- ✅ google_contacts - Added 2025-12-31
- ✅ youtube - Added 2025-12-31
- ✅ google_forms - Added 2025-12-31
- ✅ google_docs - Added 2025-12-31
- ✅ google_ads - Added 2025-12-31
- ✅ google_analytics - Added 2025-12-31

### Phase 3: Microsoft Suite (5 servers)
- microsoft_outlook
- microsoft_teams
- onedrive
- microsoft_excel
- dynamics365

### Phase 4: Project Management (9 servers)
- trello
- asana
- monday
- clickup
- jira
- confluence
- basecamp
- smartsheet
- todoist

### Phase 5: Communication (4 servers)
- discord
- twilio
- whatsapp
- telegram

### Phase 6: CRM & Sales (6 servers)
- salesforce
- pipedrive
- close_crm
- zoho_crm
- insightly
- calendly

### Phase 7: Customer Support (7 servers)
- intercom
- zendesk
- freshdesk
- helpscout
- front
- gorgias
- servicenow

### Phase 8: E-commerce & Payments (6 servers)
- shopify (with webhook support)
- woocommerce
- ebay
- etsy
- paypal
- (stripe already in Phase 1)

### Phase 9: Email Marketing (7 servers)
- klaviyo
- activecampaign
- mailerlite
- sendgrid
- mailgun
- postmark
- (mailchimp already in Phase 1)

### Phase 10: Document & Storage (4 servers)
- docusign
- pandadoc
- dropbox
- box

### Phase 11: Developer & Design (4 servers)
- gitlab
- miro
- figma
- (github already in Phase 1)

### Phase 12: Website Builders (4 servers)
- webflow
- wordpress
- wix
- squarespace

### Phase 13: Forms & Surveys (2 servers)
- typeform
- jotform

### Phase 14: Advertising (2 servers)
- meta_ads
- linkedin_ads

### Phase 15: Finance (4 servers)
- quickbooks
- xero
- freshbooks
- coda

### Phase 16: Data Processing (9 servers)
- cloudconvert
- pdfco
- docparser
- parseur
- apify
- clearbit
- hunter
- bitly
- uptimerobot

### Phase 17: Cloud Storage (3 servers)
- aws_s3
- gcs
- azure_blob

### Phase 18: Databases (5 servers)
- mysql (direct connection)
- postgresql (direct connection)
- mongodb (direct connection)
- sqlalchemy_pool (connection pooling)
- pymongo_pool (connection pooling)

### Phase 19: Analytics (5 servers)
- segment
- mixpanel
- amplitude
- bigquery
- snowflake

---

## Acceptance Criteria

### Per Server
- [ ] Definition file exists in `reference_templates/servers/definitions/{name}.py`
- [ ] Template file exists in `reference_templates/servers/templates/{name}.json`
- [ ] Template documents read vs write operations
- [ ] Server entry in `default.boot.source.json`
- [ ] Server entry in `readonly.boot.source.json`
- [ ] Server is enabled by default
- [ ] Uses shared abstractions (http_client, error_response, form_generator)
- [ ] All unit tests pass (minimum 10 tests per server)
- [ ] All integration tests pass (minimum 6 tests per server)
- [ ] 80% line coverage minimum, 100% for auth/request building
- [ ] Secret naming matches service convention
- [ ] Shows helpful form when no endpoint provided
- [ ] Returns JSON errors with `error` key
- [ ] Configurable timeout (default 60s)
- [ ] Sandbox/test account documented

### Shared Abstractions
- [ ] All 8 modules implemented
- [ ] 100% test coverage
- [ ] No secrets logged
- [ ] Retry behavior: max 3 retries, exponential backoff (2s, 4s, 8s)
- [ ] Rate limit (429) triggers retry

### Overall
- [ ] All 100+ servers implemented
- [ ] Boot images regenerate successfully
- [ ] No duplicate server names
- [ ] All tests pass in CI/CD (mocked)
- [ ] Real API tests pass with environment keys
- [ ] No security vulnerabilities
- [ ] Performance acceptable (no startup degradation)

---

## References

- Existing server patterns: `reference_templates/servers/definitions/anthropic_claude.py`
- Boot image structure: `reference_templates/default.boot.source.json`
- Test patterns: `tests/test_server_*.py`
- Integration test patterns: `tests/integration/test_server_*.py`
- API documentation links in service tables above

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| Initial | Created plan document | Claude |
| Update 1 | Resolved all 17 open questions; added shared abstractions section; revised implementation phases to start with Phase 0 (shared infrastructure); added follow-up questions | Claude |
| Update 2 | Resolved all 5 follow-up questions (Q18-Q21); confirmed top-level package location; updated OAuth manager to return tokens to caller; added separate connection/query timeouts for database servers; updated pooling servers to use generic connection strings; removed follow-up questions section | Claude |
| Update 3 | Documented enhanced Slack and Airtable error reporting and noted refactor to shared helpers | Claude |
