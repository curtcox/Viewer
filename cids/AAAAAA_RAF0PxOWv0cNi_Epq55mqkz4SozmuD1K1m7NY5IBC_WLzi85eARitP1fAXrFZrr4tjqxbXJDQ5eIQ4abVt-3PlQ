# ruff: noqa: F821, F706
"""Call the Bitly API for URL shortening and tracking."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient, HttpClientConfig, error_response,
    missing_secret_error, validation_error, generate_form, FormField,
)
import requests

API_BASE_URL = "https://api-ssl.bitly.com/v4"
DOCUMENTATION_URL = "https://dev.bitly.com/"

def main(operation: str = "", long_url: str = "", bitlink: str = "", link_id: str = "",
         timeout: int = 60, dry_run: bool = True, *, BITLY_ACCESS_TOKEN: str,
         context=None, client: Optional[ExternalApiClient] = None):
    if not BITLY_ACCESS_TOKEN:
        return missing_secret_error("BITLY_ACCESS_TOKEN")
    
    if not operation:
        return generate_form("bitly", "Bitly API",
            "Shorten and track URLs with Bitly API.",
            [FormField(name="operation", label="Operation", field_type="select",
                      options=["shorten_url", "get_link", "expand_link", "get_clicks", "create_bitlink"], required=True),
             FormField(name="long_url", label="Long URL", placeholder="https://example.com/page"),
             FormField(name="bitlink", label="Bitlink", placeholder="bit.ly/abc123"),
             FormField(name="link_id", label="Link ID", placeholder="bit.ly/abc123"),
             FormField(name="dry_run", label="Dry Run", field_type="select",
                      options=["true", "false"], default="true")],
            examples=[{"title": "Shorten URL", "code": 'operation=shorten_url&long_url=https://example.com'}],
            documentation_url=DOCUMENTATION_URL)
    
    valid_operations = ["shorten_url", "get_link", "expand_link", "get_clicks", "create_bitlink"]
    if operation not in valid_operations:
        return validation_error(f"Invalid operation: {operation}")
    
    if operation in ["shorten_url", "create_bitlink"] and not long_url:
        return validation_error(f"long_url is required for {operation}")
    if operation in ["get_link", "expand_link", "get_clicks"] and not (bitlink or link_id):
        return validation_error(f"bitlink or link_id is required for {operation}")
    
    if dry_run:
        preview = {"operation": operation, "api_endpoint": API_BASE_URL, "dry_run": True}
        if long_url:
            preview["long_url"] = long_url
        if bitlink or link_id:
            preview["bitlink"] = bitlink or link_id
        return {"output": preview, "content_type": "application/json"}
    
    if client is None:
        client = ExternalApiClient(HttpClientConfig(timeout=timeout))
    
    headers = {"Authorization": f"Bearer {BITLY_ACCESS_TOKEN}", "Content-Type": "application/json"}
    
    try:
        if operation in ["shorten_url", "create_bitlink"]:
            response = client.post(f"{API_BASE_URL}/shorten", headers=headers, json={"long_url": long_url})
        elif operation == "get_link":
            link = bitlink or link_id
            response = client.get(f"{API_BASE_URL}/bitlinks/{link}", headers=headers)
        elif operation == "expand_link":
            link = bitlink or link_id
            response = client.post(f"{API_BASE_URL}/expand", headers=headers, json={"bitlink_id": link})
        elif operation == "get_clicks":
            link = bitlink or link_id
            response = client.get(f"{API_BASE_URL}/bitlinks/{link}/clicks/summary", headers=headers)
        else:
            return validation_error(f"Unsupported operation: {operation}")
        
        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}
    
    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = e.response.text if hasattr(e, "response") and e.response else str(e)
        return error_response(f"Bitly API request failed: {error_detail}", "api_error", status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", "api_error")
