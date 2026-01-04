# ruff: noqa: F821, F706
"""Call the Clearbit API for company and person enrichment."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient, HttpClientConfig, error_response,
    missing_secret_error, validation_error, generate_form, FormField,
)
import requests

API_BASE_URL = "https://company.clearbit.com/v2"
DOCUMENTATION_URL = "https://clearbit.com/docs"

def main(operation: str = "", domain: str = "", email: str = "", query: str = "",
         timeout: int = 60, dry_run: bool = True, *, CLEARBIT_API_KEY: str,
         context=None, client: Optional[ExternalApiClient] = None):
    if not CLEARBIT_API_KEY:
        return missing_secret_error("CLEARBIT_API_KEY")
    
    if not operation:
        return generate_form("clearbit", "Clearbit API",
            "Enrich company and person data with Clearbit API.",
            [FormField(name="operation", label="Operation", field_type="select",
                      options=["enrich_company", "find_company", "enrich_person", "autocomplete"], required=True),
             FormField(name="domain", label="Domain", placeholder="example.com"),
             FormField(name="email", label="Email", placeholder="john@example.com"),
             FormField(name="query", label="Query", placeholder="Acme Corp"),
             FormField(name="dry_run", label="Dry Run", field_type="select",
                      options=["true", "false"], default="true")],
            examples=[{"title": "Enrich Company", "code": 'operation=enrich_company&domain=example.com'}],
            documentation_url=DOCUMENTATION_URL)
    
    valid_operations = ["enrich_company", "find_company", "enrich_person", "autocomplete"]
    if operation not in valid_operations:
        return validation_error(f"Invalid operation: {operation}")
    
    if operation in ["enrich_company", "find_company"] and not domain:
        return validation_error(f"domain is required for {operation}")
    if operation == "enrich_person" and not email:
        return validation_error("email is required for enrich_person")
    if operation == "autocomplete" and not query:
        return validation_error("query is required for autocomplete")
    
    if dry_run:
        preview = {"operation": operation, "api_endpoint": API_BASE_URL, "dry_run": True}
        if domain:
            preview["domain"] = domain
        if email:
            preview["email"] = email
        if query:
            preview["query"] = query
        return {"output": preview, "content_type": "application/json"}
    
    if client is None:
        client = ExternalApiClient(HttpClientConfig(timeout=timeout))
    
    headers = {"Authorization": f"Bearer {CLEARBIT_API_KEY}"}
    
    try:
        if operation == "enrich_company":
            response = client.get(f"{API_BASE_URL}/companies/find", headers=headers, params={"domain": domain})
        elif operation == "find_company":
            response = client.get(f"{API_BASE_URL}/companies/find", headers=headers, params={"domain": domain})
        elif operation == "enrich_person":
            response = client.get("https://person.clearbit.com/v2/people/find", headers=headers, params={"email": email})
        elif operation == "autocomplete":
            response = client.get("https://autocomplete.clearbit.com/v1/companies/suggest", headers=headers, params={"query": query})
        else:
            return validation_error(f"Unsupported operation: {operation}")
        
        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}
    
    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = e.response.text if hasattr(e, "response") and e.response else str(e)
        return error_response(f"Clearbit API request failed: {error_detail}", "api_error", status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", "api_error")
