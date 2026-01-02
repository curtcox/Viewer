# External Servers - Remaining Issues

**Status:** TODO
**Created:** 2026-01-02
**Related:** todo/external_servers_followup.md

## Overview

This document describes the remaining issues and improvements for external servers that were **not addressed** in the initial security fixes PR. The critical security vulnerabilities (AWS/Azure authentication, SQL injection) have been resolved. This document focuses on code quality, maintainability, and additional security hardening opportunities.

**What Was Fixed:**
- ✅ AWS Signature V4 implementation
- ✅ Azure Shared Key implementation  
- ✅ SQL injection in PostgreSQL timeout
- ✅ Azure connection string parsing improvements

**What Remains (This Document):**
- Code duplication (~9,120 lines)
- Missing shared utilities
- Inconsistent error handling
- Additional validation opportunities
- Test improvements
- Configuration standardization

---

## 1. SECURITY IMPROVEMENTS (Non-Critical)

**Status:** ✅ INFRASTRUCTURE COMPLETED - Ready for server adoption

### Shared Utilities Implemented

The following utilities have been created in `server_utils/external_api/` and are ready for gradual adoption:

1. **OperationValidator** (`operation_validator.py`) - ✅ COMPLETE
   - Standardizes operation name validation
   - Eliminates ~200 lines across 76 files
   - Comprehensive test coverage in `tests/test_operation_validator.py`

2. **CredentialValidator** (`credential_validator.py`) - ✅ COMPLETE
   - Validates required credentials/secrets
   - Eliminates ~300 lines across 70+ files
   - Comprehensive test coverage in `tests/test_credential_validator.py`

3. **PreviewBuilder** (`preview_builder.py`) - ✅ COMPLETE
   - Builds standardized preview objects for dry-run mode
   - Eliminates ~2,000 lines across 76 files
   - Includes automatic sensitive header redaction
   - Comprehensive test coverage in `tests/test_preview_builder.py`

4. **ResponseHandler** (`response_handler.py`) - ✅ COMPLETE
   - Standardized HTTP response and exception handling
   - Eliminates ~400 lines across 30+ files
   - Comprehensive test coverage in `tests/test_response_handler.py`

5. **ParameterValidator** (`parameter_validator.py`) - ✅ COMPLETE
   - Validates operation-specific parameter requirements
   - Simplifies validation logic across all servers
   - Comprehensive test coverage in `tests/test_parameter_validator.py`

All utilities are:
- ✅ Exported from `server_utils/external_api/__init__.py`
- ✅ Fully tested (112 tests, all passing)
- ✅ Documented with docstrings and examples
- ✅ Ready for incremental adoption in server definitions

**Next Steps:**
- Apply utilities to 2-3 sample servers as proof of concept
- Document migration patterns
- Gradual rollout across remaining servers

---

## 1. SECURITY IMPROVEMENTS (Non-Critical)

### 1.1 Credentials Sanitization in Preview Mode

**Priority:** MEDIUM
**Files:** mongodb.py, and potentially other servers

**Issue:** MongoDB URI sanitization could be improved:

```python
# Current (mongodb.py:23)
"uri": uri.split("@")[-1] if "@" in uri else uri,  # Hide credentials
```

**Recommendation:**
Create a consistent credential sanitization utility:

```python
# In server_utils/external_api/credential_sanitizer.py
from urllib.parse import urlparse

def sanitize_uri(uri: str) -> str:
    """Sanitize URI to hide credentials while preserving structure."""
    try:
        parsed = urlparse(uri)
        if parsed.username:
            return f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port or '***'}/{parsed.path}"
        return uri
    except Exception:
        return "***"
```

**Impact:** Better security for preview mode across all servers

---

### 1.2 SQL Query Validation

**Priority:** MEDIUM
**Files:** postgresql.py, mysql.py, snowflake.py

**Issue:** Raw SQL queries are accepted without content validation. While parameterized queries prevent injection, dangerous operations like DROP TABLE could still be executed if permissions allow.

**Recommendation:**
Add optional query pattern validation:

```python
# In server_utils/external_api/sql_validator.py
import re
from typing import Optional, Dict, Any

DANGEROUS_KEYWORDS = {"DROP", "ALTER", "GRANT", "REVOKE", "TRUNCATE"}

def validate_query_safety(query: str, allow_dangerous: bool = False) -> Optional[Dict[str, Any]]:
    """
    Validate SQL query for dangerous operations.
    
    Args:
        query: SQL query string
        allow_dangerous: If False, reject queries with dangerous keywords
        
    Returns:
        Error dict if validation fails, None if valid
    """
    if allow_dangerous:
        return None
        
    upper_query = query.upper()
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf'\b{keyword}\b', upper_query):
            return error_output(
                f"Query contains potentially dangerous keyword: {keyword}",
                status_code=403
            )
    return None
```

**Usage in servers:**
```python
def main(*, query: str, allow_dangerous_queries: bool = False, ...):
    if error := validate_query_safety(query, allow_dangerous_queries):
        return error
    # Proceed with query execution
```

**Impact:** Additional layer of protection against accidental data loss

---

### 1.3 Parameter Bounds Checking

**Priority:** LOW
**Files:** aws_s3.py, gcs.py, azure_blob.py, github.py, and 50+ other servers

**Issue:** Pagination/limit parameters have no bounds checking:

```python
max_keys: int = 1000,  # What if user passes 999999999?
```

**Recommendation:**
```python
# In server_utils/external_api/validators.py
MAX_ALLOWED_LIMIT = 10000

def validate_limit(limit: int, field_name: str = "limit") -> Optional[Dict[str, Any]]:
    """Validate pagination limit parameter."""
    if limit < 1:
        return validation_error(f"{field_name} must be positive", field=field_name)
    if limit > MAX_ALLOWED_LIMIT:
        return validation_error(
            f"{field_name} exceeds maximum of {MAX_ALLOWED_LIMIT}",
            field=field_name
        )
    return None
```

**Impact:** Prevents resource exhaustion from excessive limit values

---

## 2. CODE DUPLICATION & SHARED UTILITIES

### 2.1 Operation Validator

**Estimated Impact:** Eliminates ~200 lines across 76 files

**Current Pattern (repeated in every server):**
```python
normalized_operation = operation.lower()
if normalized_operation not in valid_operations:
    return validation_error("Unsupported operation", field="operation")
```

**Proposed Implementation:**
```python
# server_utils/external_api/operation_validator.py
from typing import Dict, Any, Optional, Set

class OperationValidator:
    """Validate operation names against allowed set."""
    
    def __init__(self, valid_operations: Set[str]):
        """
        Initialize validator with valid operations.
        
        Args:
            valid_operations: Set of allowed operation names (case-insensitive)
        """
        self.valid_operations = {op.lower() for op in valid_operations}
    
    def validate(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Validate an operation name.
        
        Args:
            operation: Operation name to validate
            
        Returns:
            Error dict if invalid, None if valid
        """
        if operation.lower() not in self.valid_operations:
            return validation_error("Unsupported operation", field="operation")
        return None
    
    def normalize(self, operation: str) -> str:
        """Return normalized (lowercase) operation name."""
        return operation.lower()
```

**Usage Example:**
```python
# In server definition
OPERATIONS = {"list_issues", "get_issue", "create_issue"}
validator = OperationValidator(OPERATIONS)

def main(*, operation: str, ...):
    if error := validator.validate(operation):
        return error
    normalized_op = validator.normalize(operation)
    # Continue with normalized_op
```

---

### 2.2 Credential Validator

**Estimated Impact:** Eliminates ~300 lines across 70+ files

**Current Pattern:**
```python
if not API_KEY:
    return error_output("Missing API_KEY", status_code=401)
if not API_SECRET:
    return error_output("Missing API_SECRET", status_code=401)
```

**Proposed Implementation:**
```python
# server_utils/external_api/credential_validator.py
from typing import Dict, Any, Optional

class CredentialValidator:
    """Validate required credentials/secrets."""
    
    @staticmethod
    def require_secrets(**secrets: str) -> Optional[Dict[str, Any]]:
        """
        Validate that all required secrets are provided.
        
        Args:
            **secrets: Keyword arguments where key is secret name and value is the secret
            
        Returns:
            Error dict if any secret is missing, None if all present
            
        Example:
            error = CredentialValidator.require_secrets(
                AWS_ACCESS_KEY_ID=access_key,
                AWS_SECRET_ACCESS_KEY=secret_key
            )
            if error:
                return error
        """
        for name, value in secrets.items():
            if not value:
                return error_output(f"Missing {name}", status_code=401)
        return None
```

---

### 2.3 Preview Builder

**Estimated Impact:** Eliminates ~2,000 lines across 76 files

**Current Pattern (every server has this function):**
```python
def _build_preview(*, operation: str, ...) -> Dict[str, Any]:
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
```

**Proposed Implementation:**
```python
# server_utils/external_api/preview_builder.py
from typing import Dict, Any, Optional

class PreviewBuilder:
    """Build standardized preview objects for dry-run mode."""
    
    @staticmethod
    def build(
        operation: str,
        url: str,
        method: str,
        auth_type: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **extra: Any
    ) -> Dict[str, Any]:
        """
        Build a preview object showing what would be executed.
        
        Args:
            operation: The operation being performed
            url: The URL that would be called
            method: HTTP method (GET, POST, etc.)
            auth_type: Authentication method description
            params: Optional query parameters
            payload: Optional request body
            headers: Optional request headers (sensitive values should be redacted)
            **extra: Additional server-specific fields to include
            
        Returns:
            Dictionary with preview information
        """
        preview: Dict[str, Any] = {
            "operation": operation,
            "url": url,
            "method": method,
            "auth": auth_type,
        }
        
        if params:
            preview["params"] = params
        
        if payload:
            preview["payload"] = payload
        
        if headers:
            # Redact sensitive headers
            safe_headers = _redact_sensitive_headers(headers)
            preview["headers"] = safe_headers
        
        if extra:
            preview.update(extra)
        
        return preview


def _redact_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact sensitive information from headers."""
    sensitive_keys = {
        "authorization",
        "x-api-key",
        "api-token",
        "x-auth-token",
        "cookie",
        "x-csrf-token",
    }
    
    return {
        key: "***" if key.lower() in sensitive_keys else value
        for key, value in headers.items()
    }
```

---

### 2.4 Response Handler

**Estimated Impact:** Eliminates ~400 lines across 30+ files

**Current Pattern:**
```python
except requests.RequestException as exc:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return error_output("Request failed", status_code=status, details=str(exc))
```

**Proposed Implementation:**
```python
# server_utils/external_api/response_handler.py
import requests
from typing import Dict, Any, Optional, Callable

class ResponseHandler:
    """Standardized handling of HTTP responses and exceptions."""
    
    @staticmethod
    def handle_request_exception(exc: requests.RequestException) -> Dict[str, Any]:
        """
        Standardized handling of requests exceptions.
        
        Args:
            exc: The RequestException that was raised
            
        Returns:
            Error response dict
        """
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output(
            "Request failed",
            status_code=status or 500,
            details=str(exc)
        )
    
    @staticmethod
    def handle_json_response(
        response: requests.Response,
        error_message_extractor: Optional[Callable[[Dict], str]] = None
    ) -> Dict[str, Any]:
        """
        Parse JSON response and handle errors consistently.
        
        Args:
            response: The HTTP response object
            error_message_extractor: Optional function to extract error message from response data
            
        Returns:
            Success dict with data or error dict
        """
        try:
            data = response.json()
        except ValueError:
            return error_output(
                "Invalid JSON response",
                status_code=response.status_code,
                details=response.text[:500]  # Limit details length
            )
        
        if not response.ok:
            message = (
                error_message_extractor(data)
                if error_message_extractor and callable(error_message_extractor)
                else "API error"
            )
            return error_output(
                message,
                status_code=response.status_code,
                response=data
            )
        
        return {"output": data}
```

---

### 2.5 Parameter Validator

**Estimated Impact:** Simplifies validation logic across all servers

**Proposed Implementation:**
```python
# server_utils/external_api/parameter_validator.py
from typing import Dict, Any, Optional, List

class ParameterValidator:
    """Validate operation-specific parameter requirements."""
    
    @staticmethod
    def validate_required_for_operation(
        operation: str,
        operation_requirements: Dict[str, List[str]],
        provided_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate that all required parameters for an operation are provided.
        
        Args:
            operation: Operation being performed
            operation_requirements: Dict mapping operations to required parameter names
            provided_params: Dict of provided parameters
            
        Returns:
            Error dict if validation fails, None if valid
            
        Example:
            REQUIREMENTS = {
                "list_buckets": ["project_id"],
                "get_object": ["bucket", "key"],
            }
            
            error = ParameterValidator.validate_required_for_operation(
                operation="get_object",
                operation_requirements=REQUIREMENTS,
                provided_params=locals()
            )
            if error:
                return error
        """
        required = operation_requirements.get(operation, [])
        for param in required:
            if param not in provided_params or provided_params[param] is None:
                return validation_error(
                    f"Missing required {param} for {operation}",
                    field=param
                )
        return None
```

---

## 3. ERROR HANDLING IMPROVEMENTS

### 3.1 Inconsistent Exception Catching

**Issue:** Recent servers (Phase 17-19) use broad exception handling:

```python
except Exception as e:
    return error_output(str(e), status_code=500)
```

Earlier servers use more specific patterns:
```python
except requests.RequestException as exc:
    # Handle specifically
except ValueError:
    # Handle JSON parsing
```

**Recommendation:**
Standardize on specific exception handling with a fallback:

```python
try:
    # Server operation
    ...
except requests.RequestException as exc:
    return ResponseHandler.handle_request_exception(exc)
except ValueError as e:
    return error_output(f"Invalid parameter format: {e}", status_code=400)
except KeyError as e:
    return error_output(f"Missing required field: {e}", status_code=400)
except Exception as e:
    # Log the full stack trace
    logger.exception("Unexpected error in server operation")
    # Return generic error to user
    return error_output("Internal server error", status_code=500)
```

**Impact:** Better error messages and debugging

---

### 3.2 Response Checking Standardization

**Issue:** Two patterns exist for checking response status:

Pattern 1 (49 files):
```python
if not response.ok:
    return error_output(...)
```

Pattern 2 (Earlier files):
```python
if not getattr(response, "ok", False):
    return error_output(...)
```

**Recommendation:**
Add helper to ResponseHandler:

```python
# In response_handler.py
@staticmethod
def check_response_ok(response) -> bool:
    """Safely check if response indicates success."""
    return getattr(response, "ok", False)
```

Then use consistently:
```python
if not ResponseHandler.check_response_ok(response):
    return error_output(...)
```

---

## 4. CONFIGURATION STANDARDIZATION

### 4.1 API Version Configuration

**Issue:** Some servers hard-code API versions:

```python
# Bad: azure_blob.py
"x-ms-version": "2021-08-06",  # No way to override
```

**Good example:**
```python
# notion.py
_DEF_VERSION = "2022-06-28"
def main(*, notion_version: str = _DEF_VERSION, ...):
```

**Recommendation:**
Make all API versions configurable:

```python
def main(
    *,
    operation: str,
    api_version: str = "2021-08-06",  # Default but overridable
    ...
):
```

---

### 4.2 Timeout Standardization

**Issue:** Inconsistent timeout defaults:
- Most servers: `timeout: int = 60`
- google_auth.py: `timeout=30`
- Database servers: separate `connection_timeout` and `query_timeout`

**Recommendation:**
Create configuration constants:

```python
# server_utils/external_api/config.py
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_CONNECTION_TIMEOUT = 10
DEFAULT_QUERY_TIMEOUT = 30

# Per-server overrides
SERVER_TIMEOUTS = {
    "aws_s3": 120,  # Large file operations
    "google_analytics": 90,  # Complex reports
}
```

---

### 4.3 Retry Configuration

**Issue:** Retry behavior is hard-coded in http_client.py:

```python
max_retries: int = 3
backoff_factor: float = 2.0
retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)
```

**Recommendation:**
Make configurable per-server:

```python
def main(
    *,
    operation: str,
    max_retries: int = 3,
    retry_backoff: float = 2.0,
    ...
):
```

---

### 4.4 Default Limits Standardization

**Issue:** Inconsistent naming and defaults:
- aws_s3.py: `max_keys: int = 1000`
- gcs.py: `max_results: int = 1000`
- mongodb.py: `limit: int = 100`
- github.py: `per_page: int = 30`

**Recommendation:**
Standardize naming while respecting API constraints:

```python
# In server_utils/external_api/config.py
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# In servers
def main(*, page_size: int = DEFAULT_PAGE_SIZE, ...):
    # Map to API-specific parameter name when making request
```

---

## 5. DATABASE SERVER ABSTRACTION

### 5.1 High Similarity Between Database Servers

**Servers:** postgresql.py, mysql.py, snowflake.py (95% similar)

**Differences:**
- Import statements (psycopg2 vs mysql.connector vs snowflake.connector)
- Connection parameter names
- Specific SQL syntax

**Proposed Solution:**
Create `server_utils/external_api/database_connection.py`:

```python
from typing import Dict, Any, Optional, List
from enum import Enum

class DatabaseDriver(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"

class DatabaseConnection:
    """Unified database connection and query execution."""
    
    DRIVER_MODULES = {
        DatabaseDriver.POSTGRESQL: "psycopg2",
        DatabaseDriver.MYSQL: "mysql.connector",
        DatabaseDriver.SNOWFLAKE: "snowflake.connector",
    }
    
    @staticmethod
    def execute_query(
        driver: DatabaseDriver,
        connection_params: Dict[str, Any],
        query: str,
        query_params: Optional[Dict[str, Any]] = None,
        connection_timeout: int = 10,
        query_timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Unified database query execution across different drivers.
        
        Args:
            driver: Database driver to use
            connection_params: Connection parameters (host, port, database, etc.)
            query: SQL query to execute
            query_params: Optional query parameters for parameterized queries
            connection_timeout: Timeout for establishing connection
            query_timeout: Timeout for query execution
            
        Returns:
            Query results or error dict
        """
        # Import appropriate driver
        # Handle connection
        # Execute query with timeout
        # Return results
        ...
```

**Impact:** Could reduce 3 servers from ~200 lines each to ~50 lines each (450 line reduction)

---

## 6. CLOUD STORAGE ABSTRACTION

### 6.1 High Similarity Between Cloud Storage Servers

**Servers:** aws_s3.py, gcs.py, azure_blob.py (90% similar)

**Common Operations:**
- list_buckets/containers
- list_objects/blobs
- get_object/blob
- put_object/blob
- delete_object/blob

**Differences:**
- Authentication mechanisms
- API endpoints
- Parameter naming

**Proposed Solution:**
```python
# server_utils/external_api/cloud_storage.py
from abc import ABC, abstractmethod

class CloudStorageProvider(ABC):
    """Abstract base class for cloud storage providers."""
    
    @abstractmethod
    def authenticate(self) -> Dict[str, str]:
        """Return authentication headers."""
        pass
    
    @abstractmethod
    def build_url(self, operation: str, **params) -> str:
        """Build the request URL for an operation."""
        pass
    
    def list_buckets(self, **kwargs):
        """List all buckets/containers."""
        # Shared implementation
        pass
    
    def list_objects(self, bucket: str, prefix: str = "", **kwargs):
        """List objects in a bucket."""
        # Shared implementation
        pass
```

**Impact:** Could reduce 3 servers from ~250 lines each to ~100 lines each (450 line reduction)

---

## 7. TEST IMPROVEMENTS

### 7.1 Property-Based Testing

**Current:** Tests use fixed examples

**Recommendation:**
Add property-based tests for dry-run mode:

```python
from hypothesis import given, strategies as st

@given(
    operation=st.sampled_from(["list_buckets", "list_objects", "get_object"]),
    bucket=st.text(min_size=1, max_size=63),
    key=st.text(min_size=1),
)
def test_dry_run_always_safe(operation, bucket, key):
    """Property test: dry-run should never make actual API calls."""
    result = aws_s3.main(
        operation=operation,
        bucket=bucket,
        key=key,
        dry_run=True,
        AWS_ACCESS_KEY_ID="test",
        AWS_SECRET_ACCESS_KEY="test",
    )
    assert "preview" in result["output"]
    assert result["output"]["message"] == "Dry run - no API call made"
```

---

### 7.2 Integration Test Suite

**Currently Missing:**
- Actual database connections (with test containers)
- Real API authentication flows
- End-to-end scenarios

**Recommendation:**
Create integration test suite using Docker Compose:

```yaml
# docker-compose.test.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: test

  mongodb:
    image: mongo:6

  localstack:  # For AWS services
    image: localstack/localstack
    environment:
      SERVICES: s3
```

---

### 7.3 Performance/Load Tests

**Recommendation:**
Test timeout and rate limiting:

```python
def test_query_timeout_enforced():
    """Verify query timeout is enforced."""
    result = postgresql.main(
        operation="query",
        query="SELECT pg_sleep(60)",  # Sleep for 60 seconds
        query_timeout=5,  # But timeout after 5 seconds
        dry_run=False,
        ...
    )
    assert "error" in result["output"]
    assert "timeout" in result["output"]["error"].lower()
```

---

### 7.4 Security Tests

**Recommendation:**
Test authentication and dangerous operations:

```python
def test_rejects_dangerous_sql_query():
    """Verify dangerous SQL patterns are caught."""
    malicious_query = "SELECT * FROM users; DROP TABLE users; --"
    result = postgresql.main(
        operation="query",
        query=malicious_query,
        allow_dangerous_queries=False,  # New parameter
        dry_run=False,
        ...
    )
    assert "error" in result["output"]
    assert result["output"]["status_code"] == 403
```

---

### 7.5 Test Organization

**Current Structure:**
```
tests/
  test_external_server_aws_s3.py
  test_external_server_github.py
  ...
```

**Recommended Structure:**
```
tests/
  unit/
    external_servers/
      test_aws_s3.py
      test_github.py
      ...
  integration/
    external_servers/
      test_database_integration.py
      test_cloud_storage_integration.py
  shared/
    test_operation_validator.py
    test_credential_validator.py
    test_preview_builder.py
    test_response_handler.py
```

---

## 8. AUTHENTICATION ABSTRACTION

### 8.1 Current Authentication Patterns

Multiple authentication patterns exist across servers:

1. **Bearer Token** (50+ servers)
2. **Basic Auth** (Snowflake, PostgreSQL, MySQL)
3. **API Key in Headers** (Various servers)
4. **OAuth/Service Account** (Google services)
5. **Signature-based** (AWS, Azure) - ✅ Now properly implemented

**Proposal:**
Create `server_utils/external_api/auth_providers.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict

class AuthProvider(ABC):
    """Base class for authentication providers."""
    
    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Return authentication headers for requests."""
        pass
    
    @abstractmethod
    def get_auth_description(self) -> str:
        """Return human-readable description for preview mode."""
        pass


class BearerAuthProvider(AuthProvider):
    """Bearer token authentication."""
    
    def __init__(self, token: str):
        self.token = token
    
    def get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_auth_description(self) -> str:
        return "Bearer Token"


class BasicAuthProvider(AuthProvider):
    """HTTP Basic authentication."""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def get_auth_headers(self) -> Dict[str, str]:
        import base64
        auth_string = f"{self.username}:{self.password}"
        encoded = base64.b64encode(auth_string.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    
    def get_auth_description(self) -> str:
        return "Basic Auth"


class ApiKeyAuthProvider(AuthProvider):
    """API key authentication (custom header)."""
    
    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name
    
    def get_auth_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key}
    
    def get_auth_description(self) -> str:
        return f"API Key ({self.header_name})"
```

---

## 9. IMPLEMENTATION ROADMAP

### Priority Levels

**HIGH PRIORITY** (Immediate value, clear benefits)
1. Shared Utilities Foundation (Section 2)
   - OperationValidator
   - CredentialValidator
   - PreviewBuilder
   - ResponseHandler
   - ParameterValidator

**MEDIUM PRIORITY** (Significant improvements)
2. Error Handling Standardization (Section 3)
3. Configuration Standardization (Section 4)
4. Security Improvements (Section 1)

**LOW PRIORITY** (Nice to have, but optional)
5. Database Server Abstraction (Section 5)
6. Cloud Storage Abstraction (Section 6)
7. Test Improvements (Section 7)
8. Authentication Abstraction (Section 8)

---

## 10. ESTIMATED IMPACT

### Code Reduction
- **Shared Utilities:** ~3,000 lines eliminated
- **Database Abstraction:** ~450 lines eliminated
- **Cloud Storage Abstraction:** ~450 lines eliminated
- **Total Potential Reduction:** ~3,900 lines (43% of duplicated code)

### Maintainability
- Consistent error handling across all servers
- Single source of truth for validation logic
- Easier to add new servers (use shared components)
- Reduced testing burden (test utilities once)

### Developer Experience
- **Time to Add New Server:** Reduce from ~4 hours to ~1 hour
- **Lines per Server:** Average ~80 lines (down from ~200)
- **Bug Fix Propagation:** Fix once in utility, benefits all servers

---

## 11. NOTES

**Important Considerations:**

1. **Backward Compatibility:** All changes must maintain existing server APIs
2. **Incremental Adoption:** Utilities can be adopted gradually, one server at a time
3. **Testing:** Each utility must have comprehensive unit tests before use
4. **Documentation:** Clear usage examples for each utility
5. **Code Review:** Each batch of server refactoring should be reviewed separately

**Success Metrics:**

- Lines of code reduced by >40%
- Test coverage maintained at >90%
- No regressions in existing functionality
- Improved error messages and consistency

---

## 12. REFERENCES

- Original planning document: `done/add_external_server_definitions.md`
- Security fixes completed: `todo/external_servers_followup.md`
- Test index: `TEST_INDEX.md`
- Existing shared utilities: `server_utils/external_api/`

---

**Document Status:** Ready for Implementation Planning
**Last Updated:** 2026-01-02
**Next Steps:** Prioritize and schedule implementation of shared utilities
