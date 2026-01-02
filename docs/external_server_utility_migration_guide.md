# Migration Guide: Adopting Shared External Server Utilities

This guide demonstrates how to refactor external server definitions to use the new shared utilities.

## Overview

Five new utilities are available in `server_utils/external_api/`:

1. **OperationValidator** - Validate and normalize operation names
2. **CredentialValidator** - Validate required credentials/secrets
3. **PreviewBuilder** - Build standardized preview objects for dry-run mode
4. **ResponseHandler** - Handle HTTP responses and exceptions consistently
5. **ParameterValidator** - Validate operation-specific parameters

## Before and After: github.py Example

### Before (161 lines)
```python
def _build_preview(...) -> Dict[str, Any]:
    # 25 lines of custom preview building logic
    ...

def main(...) -> Dict[str, Any]:
    # Manual operation validation
    normalized_operation = operation.lower()
    if normalized_operation not in {"list_issues", "create_issue", "get_issue"}:
        return validation_error("Unsupported operation", field="operation")
    
    # Manual credential validation
    if not GITHUB_TOKEN:
        return error_output("Missing GITHUB_TOKEN", status_code=401, ...)
    
    # Manual parameter validation for each operation
    if normalized_operation == "create_issue":
        if not title:
            return validation_error("Missing required title", field="title")
    elif normalized_operation == "get_issue":
        if issue_number is None:
            return validation_error("Missing required issue_number", ...)
    
    # Manual preview building
    if dry_run:
        preview = _build_preview(...)
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}
    
    # Manual exception handling
    try:
        response = api_client.get(...)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("GitHub request failed", status_code=status, ...)
    
    # Manual JSON parsing and error checking
    try:
        data = response.json()
    except ValueError:
        return error_output("Invalid JSON response", ...)
    
    if not getattr(response, "ok", False):
        return error_output(data.get("message", "GitHub API error"), ...)
```

### After (131 lines, -30 lines / -18.6%)
```python
from server_utils.external_api import (
    CredentialValidator,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
)

_OPERATIONS = {"list_issues", "create_issue", "get_issue"}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "create_issue": ["title"],
    "get_issue": ["issue_number"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)

def main(...) -> Dict[str, Any]:
    # Validate operation
    if error := _OPERATION_VALIDATOR.validate(operation):
        return error
    normalized_operation = _OPERATION_VALIDATOR.normalize(operation)
    
    # Validate credentials
    if error := CredentialValidator.require_secret(GITHUB_TOKEN, "GITHUB_TOKEN"):
        return error
    
    # Validate operation-specific parameters
    if error := _PARAMETER_VALIDATOR.validate_required(
        normalized_operation,
        {"title": title, "issue_number": issue_number},
    ):
        return error
    
    # Build preview
    if dry_run:
        preview = PreviewBuilder.build(
            operation=normalized_operation,
            url=url,
            method="POST" if normalized_operation == "create_issue" else "GET",
            auth_type="Bearer Token",
            params=params,
            payload=payload,
        )
        return PreviewBuilder.dry_run_response(preview)
    
    # Execute request with automatic exception handling
    try:
        response = api_client.get(...)
    except requests.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)
    
    # Parse JSON response with automatic error handling
    def extract_github_error(data: Dict[str, Any]) -> str:
        return data.get("message", "GitHub API error")
    
    return ResponseHandler.handle_json_response(response, extract_github_error)
```

## Step-by-Step Migration

### 1. Update Imports

Add the utility imports:
```python
from server_utils.external_api import (
    CredentialValidator,
    OperationValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
)
```

### 2. Define Operation Validator (Module Level)

Replace inline operation checking:
```python
# Before
normalized_operation = operation.lower()
if normalized_operation not in {"list", "get", "create"}:
    return validation_error("Unsupported operation", field="operation")

# After (at module level)
_OPERATIONS = {"list", "get", "create"}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)

# In main function
if error := _OPERATION_VALIDATOR.validate(operation):
    return error
normalized_operation = _OPERATION_VALIDATOR.normalize(operation)
```

### 3. Define Parameter Validator (Module Level)

Replace inline parameter checks:
```python
# Before
if operation == "get" and not id:
    return validation_error("Missing required id", field="id")

# After (at module level)
_PARAMETER_REQUIREMENTS = {
    "get": ["id"],
    "create": ["name", "data"],
}
_PARAMETER_VALIDATOR = ParameterValidator(_PARAMETER_REQUIREMENTS)

# In main function
if error := _PARAMETER_VALIDATOR.validate_required(
    normalized_operation,
    {"id": id, "name": name, "data": data},
):
    return error
```

### 4. Use CredentialValidator

Replace inline credential checks:
```python
# Before
if not API_KEY:
    return error_output("Missing API_KEY", status_code=401)
if not API_SECRET:
    return error_output("Missing API_SECRET", status_code=401)

# After
if error := CredentialValidator.require_secrets(
    API_KEY=API_KEY,
    API_SECRET=API_SECRET,
):
    return error
```

For optional authentication methods:
```python
# When API_KEY OR OAUTH_TOKEN can be used
if error := CredentialValidator.require_one_of(
    API_KEY=API_KEY,
    OAUTH_TOKEN=OAUTH_TOKEN,
):
    return error
```

### 5. Replace Custom Preview Building

Replace custom `_build_preview` function:
```python
# Before
def _build_preview(...) -> Dict[str, Any]:
    preview = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": auth_type,
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview

# In main
if dry_run:
    preview = _build_preview(...)
    return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

# After
if dry_run:
    preview = PreviewBuilder.build(
        operation=normalized_operation,
        url=url,
        method=method,
        auth_type=auth_type,
        params=params,
        payload=payload,
    )
    return PreviewBuilder.dry_run_response(preview)
```

### 6. Use ResponseHandler for Exceptions

Replace custom exception handling:
```python
# Before
try:
    response = api_client.get(...)
except requests.RequestException as exc:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return error_output("Request failed", status_code=status, details=str(exc))

# After
try:
    response = api_client.get(...)
except requests.RequestException as exc:
    return ResponseHandler.handle_request_exception(exc)
```

### 7. Use ResponseHandler for JSON Parsing

Replace custom JSON parsing and error checking:
```python
# Before
try:
    data = response.json()
except ValueError:
    return error_output(
        "Invalid JSON response",
        status_code=getattr(response, "status_code", None),
        details=getattr(response, "text", None),
    )

if not getattr(response, "ok", False):
    return error_output(
        data.get("message", "API error"),
        status_code=response.status_code,
        response=data,
    )

return {"output": data}

# After
def extract_error_message(data: Dict[str, Any]) -> str:
    return data.get("message", "API error")

return ResponseHandler.handle_json_response(response, extract_error_message)
```

## Common Patterns

### AWS-Style Credentials
```python
if error := CredentialValidator.require_secrets(
    AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY,
):
    return error
```

### Database-Style Operations
```python
_OPERATIONS = {"query", "insert", "update", "delete"}
_OPERATION_VALIDATOR = OperationValidator(_OPERATIONS)
_PARAMETER_REQUIREMENTS = {
    "query": ["query_text"],
    "insert": ["table", "data"],
    "update": ["table", "id", "data"],
    "delete": ["table", "id"],
}
```

### Cloud Storage Operations
```python
_OPERATIONS = {"list_buckets", "list_objects", "get_object", "put_object"}
_PARAMETER_REQUIREMENTS = {
    "list_objects": ["bucket"],
    "get_object": ["bucket", "key"],
    "put_object": ["bucket", "key", "body"],
}
```

## Benefits

1. **Code Reduction**: 15-20% reduction in lines per server
2. **Consistency**: Standardized error messages and response formats
3. **Maintainability**: Fix bugs once in utilities, all servers benefit
4. **Testing**: Utilities are comprehensively tested (112 tests)
5. **Security**: Automatic sensitive header redaction in previews
6. **Better Errors**: More informative error messages with context

## Migration Checklist

When refactoring a server:

- [ ] Add utility imports
- [ ] Create module-level validators (operation, parameter)
- [ ] Replace inline credential validation with CredentialValidator
- [ ] Replace inline operation validation with OperationValidator
- [ ] Replace inline parameter validation with ParameterValidator
- [ ] Remove custom `_build_preview` function
- [ ] Replace preview building with PreviewBuilder
- [ ] Replace exception handling with ResponseHandler
- [ ] Replace JSON parsing with ResponseHandler
- [ ] Update tests if error messages changed
- [ ] Run tests to verify functionality
- [ ] Count line reduction and update documentation

## Tips

1. **Start with simple servers**: Pick servers with basic operations first
2. **Test incrementally**: Run tests after each change
3. **Update error message tests**: Some tests expect specific error text
4. **Keep limit validators**: These work alongside the new utilities
5. **Preserve server-specific logic**: Only refactor common patterns
6. **Document improvements**: Track line reductions and benefits

## Questions or Issues?

See the utility implementations in:
- `server_utils/external_api/operation_validator.py`
- `server_utils/external_api/credential_validator.py`
- `server_utils/external_api/parameter_validator.py`
- `server_utils/external_api/preview_builder.py`
- `server_utils/external_api/response_handler.py`

And their tests in:
- `tests/test_operation_validator.py`
- `tests/test_credential_validator.py`
- `tests/test_parameter_validator.py`
- `tests/test_preview_builder.py`
- `tests/test_response_handler.py`
