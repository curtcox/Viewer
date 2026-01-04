# ruff: noqa: F821, F706
"""Call the UptimeRobot API for uptime monitoring."""

from typing import Optional
from server_utils.external_api import (
    ExternalApiClient, HttpClientConfig, error_response,
    missing_secret_error, validation_error, generate_form, FormField,
)
import requests

API_BASE_URL = "https://api.uptimerobot.com/v2"
DOCUMENTATION_URL = "https://uptimerobot.com/api/"

def main(operation: str = "", monitor_id: str = "", url: str = "", friendly_name: str = "",
         monitor_type: str = "1", timeout: int = 60, dry_run: bool = True,
         *, UPTIMEROBOT_API_KEY: str, context=None, client: Optional[ExternalApiClient] = None):
    if not UPTIMEROBOT_API_KEY:
        return missing_secret_error("UPTIMEROBOT_API_KEY")
    
    if not operation:
        return generate_form("uptimerobot", "UptimeRobot API",
            "Monitor website uptime with UptimeRobot API.",
            [FormField(name="operation", label="Operation", field_type="select",
                      options=["get_monitors", "new_monitor", "edit_monitor", "delete_monitor", "get_alert_contacts"], required=True),
             FormField(name="monitor_id", label="Monitor ID", placeholder="123456"),
             FormField(name="url", label="URL", placeholder="https://example.com"),
             FormField(name="friendly_name", label="Name", placeholder="My Website"),
             FormField(name="monitor_type", label="Type", placeholder="1", help_text="1=HTTP, 2=Keyword, etc"),
             FormField(name="dry_run", label="Dry Run", field_type="select",
                      options=["true", "false"], default="true")],
            examples=[{"title": "Get Monitors", "code": 'operation=get_monitors'}],
            documentation_url=DOCUMENTATION_URL)
    
    valid_operations = ["get_monitors", "new_monitor", "edit_monitor", "delete_monitor", "get_alert_contacts"]
    if operation not in valid_operations:
        return validation_error(f"Invalid operation: {operation}")
    
    if operation == "new_monitor" and not (url and friendly_name):
        return validation_error("url and friendly_name are required for new_monitor")
    if operation in ["edit_monitor", "delete_monitor"] and not monitor_id:
        return validation_error(f"monitor_id is required for {operation}")
    
    if dry_run:
        preview = {"operation": operation, "api_endpoint": API_BASE_URL, "dry_run": True}
        if monitor_id:
            preview["monitor_id"] = monitor_id
        if url:
            preview["url"] = url
        if friendly_name:
            preview["friendly_name"] = friendly_name
        return {"output": preview, "content_type": "application/json"}
    
    if client is None:
        client = ExternalApiClient(HttpClientConfig(timeout=timeout))
    
    headers = {"Content-Type": "application/json"}
    
    try:
        payload = {"api_key": UPTIMEROBOT_API_KEY, "format": "json"}
        
        if operation == "get_monitors":
            response = client.post(f"{API_BASE_URL}/getMonitors", headers=headers, json=payload)
        elif operation == "new_monitor":
            payload.update({"url": url, "friendly_name": friendly_name, "type": monitor_type})
            response = client.post(f"{API_BASE_URL}/newMonitor", headers=headers, json=payload)
        elif operation == "edit_monitor":
            payload["id"] = monitor_id
            if url:
                payload["url"] = url
            if friendly_name:
                payload["friendly_name"] = friendly_name
            response = client.post(f"{API_BASE_URL}/editMonitor", headers=headers, json=payload)
        elif operation == "delete_monitor":
            payload["id"] = monitor_id
            response = client.post(f"{API_BASE_URL}/deleteMonitor", headers=headers, json=payload)
        elif operation == "get_alert_contacts":
            response = client.post(f"{API_BASE_URL}/getAlertContacts", headers=headers, json=payload)
        else:
            return validation_error(f"Unsupported operation: {operation}")
        
        response.raise_for_status()
        return {"output": response.json(), "content_type": "application/json"}
    
    except requests.RequestException as e:
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        error_detail = e.response.text if hasattr(e, "response") and e.response else str(e)
        return error_response(f"UptimeRobot API request failed: {error_detail}", "api_error", status_code)
    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}", "api_error")
