# ruff: noqa: F821, F706
"""Send events to Amplitude analytics platform."""

from __future__ import annotations

from typing import Any, Dict, Optional
import json

from server_utils.external_api import ExternalApiClient, error_output, validation_error


_DEFAULT_CLIENT = ExternalApiClient()


def _build_preview(
    *,
    operation: str,
    event_type: Optional[str],
    user_id: Optional[str],
    event_properties: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a preview of the Amplitude operation."""
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": "https://api2.amplitude.com/2/httpapi",
        "method": "POST",
        "auth": "API Key",
    }
    if event_type:
        preview["event_type"] = event_type
    if user_id:
        preview["user_id"] = user_id
    if event_properties:
        preview["event_properties"] = event_properties
    return preview


def main(
    *,
    operation: str = "track",
    event_type: str = "",
    user_id: str = "",
    device_id: str = "",
    event_properties: str = "{}",
    user_properties: str = "{}",
    AMPLITUDE_API_KEY: str = "",
    AMPLITUDE_SECRET_KEY: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Send events to Amplitude analytics platform.
    
    Operations:
    - track: Track events
    - identify: Update user properties
    """
    
    normalized_operation = operation.lower()
    valid_operations = {"track", "identify"}
    
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")
    
    # Validate credentials
    if not AMPLITUDE_API_KEY:
        return error_output("Missing AMPLITUDE_API_KEY", status_code=401)
    
    # Validate required fields
    if not user_id and not device_id:
        return validation_error("Either user_id or device_id is required", field="user_id/device_id")
    
    if normalized_operation == "track" and not event_type:
        return validation_error("event_type is required for track operation", field="event_type")
    
    # Parse JSON fields
    try:
        parsed_event_properties = json.loads(event_properties) if isinstance(event_properties, str) else event_properties
        parsed_user_properties = json.loads(user_properties) if isinstance(user_properties, str) else user_properties
    except json.JSONDecodeError as e:
        return validation_error(f"Invalid JSON: {str(e)}", field="event_properties/user_properties")
    
    # Return preview if in dry-run mode
    if dry_run:
        return {
            "output": _build_preview(
                operation=normalized_operation,
                event_type=event_type if event_type else None,
                user_id=user_id if user_id else device_id,
                event_properties=parsed_event_properties if parsed_event_properties else None,
            )
        }
    
    # Execute actual API call
    api_client = client or _DEFAULT_CLIENT
    
    try:
        # Build event payload
        event: Dict[str, Any] = {}
        
        if user_id:
            event["user_id"] = user_id
        if device_id:
            event["device_id"] = device_id
        
        if normalized_operation == "track":
            event["event_type"] = event_type
            if parsed_event_properties:
                event["event_properties"] = parsed_event_properties
        
        elif normalized_operation == "identify":
            event["event_type"] = "$identify"
            if parsed_user_properties:
                event["user_properties"] = parsed_user_properties
        
        payload = {
            "api_key": AMPLITUDE_API_KEY,
            "events": [event],
        }
        
        url = "https://api2.amplitude.com/2/httpapi"
        
        response = api_client.post(
            url=url,
            json=payload,
            timeout=timeout,
        )
        
        if not response.ok:
            return error_output(
                f"Amplitude API error: {response.text}",
                status_code=response.status_code,
                response=response.text,
            )
        
        return {"output": response.json()}
    
    except Exception as e:
        return error_output(str(e), status_code=500)
