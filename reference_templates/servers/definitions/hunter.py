# ruff: noqa: F821, F706
"""Call the Hunter.io API for email finding and verification."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient, HttpClientConfig, error_response,
    missing_secret_error, validation_error, generate_form, FormField,
)
import requests

API_BASE_URL = "https://api.hunter.io/v2"
DOCUMENTATION_URL = "https://hunter.io/api-documentation"

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
    
    valid_operations = ["domain_search", "email_finder", "email_verifier", "email_count"]
    if operation not in valid_operations:
        return validation_error(f"Invalid operation: {operation}")
    
    if operation in ["domain_search", "email_count"] and not domain:
        return validation_error(f"domain is required for {operation}")
    if operation == "email_finder" and not (domain and first_name and last_name):
        return validation_error("domain, first_name, and last_name are required for email_finder")
    if operation == "email_verifier" and not email:
        return validation_error("email is required for email_verifier")
    
    if dry_run:
        preview = {"operation": operation, "api_endpoint": API_BASE_URL, "dry_run": True}
        if domain:
            preview["domain"] = domain
        if first_name:
            preview["first_name"] = first_name
        if last_name:
            preview["last_name"] = last_name
        if email:
            preview["email"] = email
        return {"output": preview, "content_type": "application/json"}
    
    if client is None:
        client = ExternalApiClient(HttpClientConfig(timeout=timeout))
    
    headers = {"Content-Type": "application/json"}
    params = {"api_key": HUNTER_API_KEY}
    
    try:
        if operation == "domain_search":
            params["domain"] = domain
            response = client.get(f"{API_BASE_URL}/domain-search", headers=headers, params=params)
        elif operation == "email_finder":
            params.update({"domain": domain, "first_name": first_name, "last_name": last_name})
            response = client.get(f"{API_BASE_URL}/email-finder", headers=headers, params=params)
        elif operation == "email_verifier":
            params["email"] = email
            response = client.get(f"{API_BASE_URL}/email-verifier", headers=headers, params=params)
        elif operation == "email_count":
            params["domain"] = domain
            response = client.get(f"{API_BASE_URL}/email-count", headers=headers, params=params)
        else:
            return validation_error(f"Unsupported operation: {operation}")
        
        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}
    
    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = e.response.text if hasattr(e, "response") and e.response else str(e)
        return error_response(f"Hunter API request failed: {error_detail}", "api_error", status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", "api_error")
