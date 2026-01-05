# ruff: noqa: F821, F706
"""Send events to Mixpanel analytics platform."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json
import base64

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    event: Optional[str],
    distinct_id: Optional[str],
    properties: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a preview of the Mixpanel operation."""
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": "https://api.mixpanel.com/" + operation,
        "method": "POST",
        "auth": "Mixpanel token",
    }
    if event:
        preview["event"] = event
    if distinct_id:
        preview["distinct_id"] = distinct_id
    if properties:
        preview["properties"] = properties
    return preview


def main(
    *,
    operation: str = "track",
    event: str = "",
    distinct_id: str = "",
    properties: str = "{}",
    set_properties: str = "{}",
    MIXPANEL_TOKEN: str = "",
    MIXPANEL_API_SECRET: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Send events to Mixpanel analytics platform.
    
    Operations:
    - track: Track events
    - engage: Update user profile properties
    - import: Import historical events
    """
    
    normalized_operation = operation.lower()
    valid_operations = {"track", "engage", "import"}
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not MIXPANEL_TOKEN:
        return error_output("Missing MIXPANEL_TOKEN", status_code=401)
    
    # Validate required fields
    if not distinct_id:
        return validation_error("distinct_id is required", field="distinct_id")
    
    if normalized_operation == "track" and not event:
        return validation_error("Event name is required for track operation", field="event")
    
    # Parse JSON fields
    try:
        parsed_properties = json.loads(properties) if isinstance(properties, str) else properties
        parsed_set_properties = json.loads(set_properties) if isinstance(set_properties, str) else set_properties
    except json.JSONDecodeError as e:
        return validation_error(f"Invalid JSON: {str(e)}", field="properties")
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                event=event if event else None,
                distinct_id=distinct_id,
                properties=parsed_properties if parsed_properties else None,
            )
        }
    
    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT
    
    try:
        # Build payload based on operation
        if normalized_operation == "track":
            payload = {
                "event": event,
                "properties": {
                    "token": MIXPANEL_TOKEN,
                    "distinct_id": distinct_id,
                    **parsed_properties,
                }
            }
            url = "https://api.mixpanel.com/track"
            data = [payload]
        
        elif normalized_operation == "engage":
            payload = {
                "$token": MIXPANEL_TOKEN,
                "$distinct_id": distinct_id,
                "$set": parsed_set_properties,
            }
            url = "https://api.mixpanel.com/engage"
            data = [payload]
        
        elif normalized_operation == "import":
            if not MIXPANEL_API_SECRET:
                return error_output("MIXPANEL_API_SECRET required for import", status_code=401)
            
            payload = {
                "event": event,
                "properties": {
                    "token": MIXPANEL_TOKEN,
                    "distinct_id": distinct_id,
                    **parsed_properties,
                }
            }
            url = "https://api.mixpanel.com/import"
            data = [payload]
        
        # Encode data as base64 for Mixpanel API
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        # Add API secret for import
        if normalized_operation == "import":
            auth_string = f"{MIXPANEL_API_SECRET}:"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
        
        response = api_client.post(
            url=url,
            headers=headers,
            data={"data": encoded_data},
            timeout=timeout,
        )
        
        if not response.ok:
            return error_output(
                f"Mixpanel API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )
        
        return {"output": {"status": response.text, "status_code": response.status_code}}
    
    except Exception as e:
        return error_output(str(e), status_code=500)
