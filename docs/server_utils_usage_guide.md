# Server Utils Usage Guide

This document provides examples and patterns for using the `server_utils.external_api` utilities to create consistent, maintainable external API server definitions with reduced complexity.

## Overview

The `server_utils.external_api` module provides utilities that help reduce code duplication and complexity in external API server definitions. When used consistently, these utilities can reduce a typical server definition's complexity from D/E/F (21-58) to B/C (6-15).

## Available Utilities

### 1. OperationValidator

**Purpose:** Validate operation names against an allowed set with consistent error messages.

**Benefits:**
- Eliminates manual if-elif chains for operation validation
- Provides normalized operation names
- Consistent error messages

**Example:**

```python
from server_utils.external_api import OperationValidator

# Define at module level
_OPERATIONS = {"list_items", "get_item", "create_item", "delete_item"}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)

def main(operation: str = "list_items", **kwargs):
    # Validate and normalize operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)
    
    # Use normalized_operation throughout the function
    # ...
```

### 2. ParameterValidator

**Purpose:** Validate operation-specific required parameters.

**Benefits:**
- Centralizes parameter requirements in one place
- Eliminates repeated parameter validation code
- Consistent error messages with helpful details

**Example:**

```python
from server_utils.external_api import ParameterValidator

# Define parameter requirements at module level
_PARAMETER_REQUIREMENTS = {
    "get_item": ["item_id"],
    "create_item": ["name"],
    "delete_item": ["item_id"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)

def main(operation: str, item_id: str = "", name: str = "", **kwargs):
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)
    
    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {"item_id": item_id, "name": name}
    ):
        return error
    
    # Continue with validated parameters
    # ...
```

### 3. CredentialValidator

**Purpose:** Validate API credentials and secrets.

**Benefits:**
- Consistent credential validation
- Clear error messages for missing credentials
- Reduces boilerplate

**Example:**

```python
from server_utils.external_api import CredentialValidator

def main(API_TOKEN: str = "", **kwargs):
    # Validate required secret
    if error := CredentialValidator.require_secret(API_TOKEN, "API_TOKEN"):
        return error
    
    # Continue with validated credential
    # ...
```

### 4. PreviewBuilder

**Purpose:** Build standardized preview responses for dry-run mode.

**Benefits:**
- Consistent preview format across all servers
- Automatic sensitive header redaction
- Eliminates preview-building duplication

**Example:**

```python
from server_utils.external_api import PreviewBuilder

def main(operation: str, dry_run: bool = True, **kwargs):
    # ... validate and prepare request details ...
    
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Bearer Token",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)
    
    # ... execute actual request ...
```

### 5. ResponseHandler

**Purpose:** Standardized HTTP response and exception handling.

**Benefits:**
- Consistent error handling
- Simplified response parsing
- Reduces try-except boilerplate

**Example:**

```python
import requests
from server_utils.external_api import ResponseHandler

def main(**kwargs):
    # ... prepare request ...
    
    try:
        response = api_client.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)
    
    # Extract error message from API response (optional custom extractor)
    def extract_error(data):
        return data.get("error", {}).get("message", "API error")
    
    return ResponseHandler.handle_json_response(response, extract_error)
```

## Complete Example: Recommended Pattern

Here's a complete example showing how to use all utilities together:

```python
# ruff: noqa: F821, F706
"""Example external API server using server_utils patterns."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from server_utils.external_api import (
    CredentialValidator,
    ExternalApiClient,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
)

# Module-level configuration
_DEFAULT_CLIENT = ExternalApiClient()
_OPERATIONS = {"list_items", "get_item", "create_item", "delete_item"}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "get_item": ["item_id"],
    "create_item": ["name"],
    "delete_item": ["item_id"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)


def main(
    *,
    operation: str = "list_items",
    item_id: str = "",
    name: str = "",
    API_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """Example API server following best practices."""

    # Step 1: Validate operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)

    # Step 2: Validate credentials
    if error := CredentialValidator.require_secret(API_TOKEN, "API_TOKEN"):
        return error

    # Step 3: Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {"item_id": item_id, "name": name}
    ):
        return error

    api_client = client or _DEFAULT_CLIENT

    # Step 4: Build request details
    base_url = "https://api.example.com"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    params: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    method = "GET"

    if normalized_operation == "list_items":
        url = f"{base_url}/items"
    elif normalized_operation == "get_item":
        url = f"{base_url}/items/{item_id}"
    elif normalized_operation == "create_item":
        url = f"{base_url}/items"
        method = "POST"
        payload = {"name": name}
    elif normalized_operation == "delete_item":
        url = f"{base_url}/items/{item_id}"
        method = "DELETE"
    else:
        url = f"{base_url}/{normalized_operation}"

    # Step 5: Return preview in dry-run mode
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method=method,
            auth_type="Bearer Token",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)

    # Step 6: Execute request with standardized error handling
    try:
        if method == "GET":
            response = api_client.get(url, headers=headers, params=params, timeout=timeout)
        elif method == "POST":
            response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
        elif method == "DELETE":
            response = api_client.delete(url, headers=headers, timeout=timeout)
        else:
            response = api_client.request(method, url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Step 7: Parse response with standardized handling
    def extract_error(data: Dict[str, Any]) -> str:
        return data.get("message", "API error")

    return ResponseHandler.handle_json_response(response, extract_error)
```

## Complexity Reduction

Using these utilities consistently can significantly reduce complexity:

### Before (Typical Pattern - Complexity D/E/F):
- 200-300 lines of code
- Manual operation validation with if-elif chains (10-20 branches)
- Duplicate URL construction (once for preview, once for execution)
- Repeated credential checking
- Inconsistent error handling
- Complexity score: 23-58 (D/E/F)

### After (Using Server Utils - Complexity B/C):
- 100-150 lines of code
- Declarative operation and parameter configuration
- Single URL construction
- Standardized validation
- Consistent error handling
- Complexity score: 8-15 (B/C)

## Migration Guide

To migrate an existing server definition:

1. **Add imports:**
   ```python
   from server_utils.external_api import (
       CredentialValidator,
       OperationValidator,
       ParameterValidator,
       PreviewBuilder,
       ResponseHandler,
   )
   ```

2. **Define module-level validators:**
   ```python
   _OPERATIONS = {"op1", "op2", "op3"}
   _OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
   _PARAMETER_REQUIREMENTS = {
       "op1": ["param1", "param2"],
       "op2": ["param3"],
   }
   _PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)
   ```

3. **Replace manual validation with validator calls:**
   - Replace `if operation not in {...}` with `_OPERATION_VALIDATOR.validate()`
   - Replace parameter checks with `_PARAMETER_VALIDATOR.validate_required()`
   - Replace credential checks with `CredentialValidator.require_secret()`

4. **Use PreviewBuilder for dry-run:**
   - Replace manual preview dict construction with `PreviewBuilder.build()`
   - Use `PreviewBuilder.dry_run_response()` for the return value

5. **Use ResponseHandler for error handling:**
   - Wrap API calls with `ResponseHandler.handle_request_exception()`
   - Use `ResponseHandler.handle_json_response()` for response parsing

6. **Test thoroughly:**
   - Ensure all existing tests pass
   - Verify preview responses match expected format
   - Check error messages are clear and helpful

## Additional Resources

- See `reference/templates/servers/definitions/github.py` for a complete working example
- Module documentation in `server_utils/external_api/`
- Radon analysis improvements: `todo/changes_to_consider_based_on_radon.md`
