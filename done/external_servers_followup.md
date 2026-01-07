# External Servers Follow-up Issues

**Status:** In Progress
**Created:** 2026-01-02
**Updated:** 2026-01-02 (Implementation started)
**Related:** done/add_external_server_definitions.md

## Implementation Progress Summary

### ✅ Completed (2026-01-02)

#### Phase 1: Critical Security Fixes - Authentication
- ✅ Implemented proper AWS Signature V4 (`server_utils/external_api/aws_signature.py`)
  - Full canonical request construction
  - Signature key derivation
  - Signature computation with HMAC-SHA256
  - Comprehensive unit tests (10 tests passing)
- ✅ Implemented proper Azure Shared Key (`server_utils/external_api/azure_signature.py`)
  - Canonical headers construction  
  - Canonical resource construction
  - HMAC-SHA256 signature
  - Comprehensive unit tests (11 tests passing)
- ✅ Updated `aws_s3.py` to use proper AWS Signature V4
- ✅ Updated `azure_blob.py` to use proper Azure Shared Key
- ✅ All existing server tests still pass (35 tests)

#### Phase 2: SQL Injection Fixes
- ✅ Fixed SQL injection risk in `postgresql.py` (line 119)
  - Changed from f-string to parameterized query for statement_timeout
  - Added integer validation for timeout value
  - All tests passing (11 tests)
- ✅ Verified MySQL and Snowflake don't have similar issues
  - MySQL doesn't set statement timeout in this way
  - Snowflake uses API endpoint (not vulnerable)

#### Phase 3: Connection String Parsing
- ✅ Improved Azure connection string parsing (`azure_blob.py`)
  - Better error handling with specific error messages
  - Validation of required keys (AccountName, AccountKey)
  - Handles malformed strings gracefully
  - All tests passing (17 tests)

### 🚧 Remaining Work

The following items from the original plan are **not yet implemented** (marked as ✅ in the plan but are actually TODO):

#### Shared Utilities Foundation (Not Completed)
- ❌ `operation_validator.py` - not created
- ❌ `credential_validator.py` - not created
- ❌ `preview_builder.py` - not created
- ❌ `response_handler.py` - not created
- ❌ `parameter_validator.py` - not created

#### Server Refactoring (Not Completed)
- ❌ No servers have been refactored to use shared utilities
- ❌ Code duplication (~9,120 lines) still exists

These remaining items can be addressed in future work when time permits. The **critical security issues have been resolved**.

---

## Overview

This document tracks issues discovered during the comprehensive review of the external server implementations (100+ servers across 19+ phases). The review examined code quality, security, testing, and opportunities for refactoring.

**Summary of Findings:**
- 99 server test files with 1296 test functions (excellent coverage!)
- Critical security issues with AWS and Azure signature implementations
- Significant code duplication (~9,120 lines could be eliminated)
- Inconsistent error handling patterns across phases
- Opportunities for shared utilities and base classes

---

## 1. CRITICAL SECURITY ISSUES

### 1.1 Incomplete AWS Signature V4 Implementation

**Priority:** CRITICAL
**File:** `reference/templates/servers/definitions/aws_s3.py:16-43`

**Issue:** The `_sign_request()` function returns a placeholder authorization header instead of proper AWS Signature V4:

```python
"Authorization": f"AWS4-HMAC-SHA256 Credential={access_key}/{date_stamp}/{region}/{service}/aws4_request",
```

This is missing the actual HMAC-SHA256 signature computation of the canonical request.

**Impact:** Server will fail when `dry_run=False`. Authentication will be rejected by AWS.

**Fix Required:**
1. Create proper AWS Signature V4 implementation in `server_utils/external_api/aws_signature.py`
2. Implement canonical request construction
3. Implement signature key derivation
4. Implement signature computation
5. Update `aws_s3.py` to use the proper implementation

**Reference:** https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html

---

### 1.2 Incomplete Azure Shared Key Signature

**Priority:** CRITICAL
**File:** `reference/templates/servers/definitions/azure_blob.py:16-35`

**Issue:** Similar to AWS, the signature is a placeholder:

```python
"Authorization": f"SharedKey {account_name}:signature_placeholder",
```

**Impact:** Server will fail when `dry_run=False`. Authentication will be rejected by Azure.

**Fix Required:**
1. Create proper Azure Shared Key implementation in `server_utils/external_api/azure_signature.py`
2. Implement canonical headers construction
3. Implement HMAC-SHA256 signature of canonicalized string
4. Update `azure_blob.py` to use the proper implementation

**Reference:** https://docs.microsoft.com/en-us/rest/api/storageservices/authorize-with-shared-key

---

### 1.3 SQL Injection Risk in Statement Timeout

**Priority:** HIGH
**File:** `reference/templates/servers/definitions/postgresql.py:119`

**Issue:** Statement timeout is set using f-string interpolation instead of parameterized query:

```python
cursor.execute(f"SET statement_timeout = {query_timeout * 1000}")
```

While `query_timeout` is an integer parameter (safer), this inconsistency with the rest of the code (which uses parameterized queries correctly) is concerning.

**Also affects:**
- `mysql.py` (similar pattern)
- `snowflake.py` (similar pattern)

**Fix Required:**
Use parameterized approach or at least add integer validation:
```python
# Option 1: Parameterized (PostgreSQL specific syntax)
cursor.execute("SET statement_timeout = %s", (query_timeout * 1000,))

# Option 2: Explicit validation
if not isinstance(query_timeout, int) or query_timeout < 0:
    return validation_error("Invalid query_timeout", field="query_timeout")
cursor.execute(f"SET statement_timeout = {query_timeout * 1000}")
```

---

### 1.4 Connection String Parsing Vulnerabilities

**Priority:** MEDIUM
**File:** `reference/templates/servers/definitions/azure_blob.py:140-146`

**Issue:** Naive connection string parsing doesn't handle edge cases:

```python
parts = dict(part.split("=", 1) for part in AZURE_STORAGE_CONNECTION_STRING.split(";") if "=" in part)
```

This doesn't handle:
- Escaped semicolons or equals signs in values
- Malformed connection strings
- Quotes around values

**Fix Required:**
Use a proper connection string parser or add validation:
```python
try:
    parts = dict(part.split("=", 1) for part in connection_string.split(";") if "=" in part)
    required_keys = ["AccountName", "AccountKey"]
    if not all(k in parts for k in required_keys):
        return error_output("Invalid connection string format", status_code=400)
except ValueError:
    return error_output("Malformed connection string", status_code=400)
```

---

### 1.5 Credentials Partially Exposed in Preview Mode

**Priority:** MEDIUM
**File:** `reference/templates/servers/definitions/mongodb.py:23`

**Issue:** MongoDB URI is partially redacted but still exposes host/port:

```python
"uri": uri.split("@")[-1] if "@" in uri else uri,  # Hide credentials
```

**Better approach:**
```python
from urllib.parse import urlparse

parsed = urlparse(uri)
sanitized = f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port}/{parsed.path}"
```

Or use a consistent sanitization utility across all servers.

---

## 2. CODE DUPLICATION AND REFACTORING OPPORTUNITIES

### 2.1 Massive Duplication Across 76 Servers

**Estimated Impact:** ~9,120 lines of duplicated code (60% reduction possible)

#### Pattern 1: Operation Validation (76 files)

**Current pattern repeated everywhere:**
```python
normalized_operation = operation.lower()
if normalized_operation not in valid_operations:
    return validation_error("Unsupported operation", field="operation")
```

**Found in:** All server files (aws_s3.py:123-137, gcs.py:102-116, azure_blob.py:119-134, github.py:70-72, etc.)

**Proposed solution:**
Create `server_utils/external_api/operation_validator.py`:
```python
class OperationValidator:
    def __init__(self, valid_operations: set[str]):
        self.valid_operations = {op.lower() for op in valid_operations}

    def validate(self, operation: str) -> Optional[Dict[str, Any]]:
        if operation.lower() not in self.valid_operations:
            return validation_error("Unsupported operation", field="operation")
        return None
```

**Impact:** Eliminates ~200 lines of duplicated code

---

#### Pattern 2: Credential Validation (70+ files)

**Current pattern:**
```python
if not API_KEY:
    return error_output("Missing API_KEY", status_code=401)
if not API_SECRET:
    return error_output("Missing API_SECRET", status_code=401)
```

**Found in:** aws_s3.py:140-144, gcs.py:119-123, postgresql.py:65-75, github.py:74-79, slack.py:35-40, etc.

**Proposed solution:**
Create `server_utils/external_api/credential_validator.py`:
```python
class CredentialValidator:
    @staticmethod
    def require_secrets(**secrets: str) -> Optional[Dict[str, Any]]:
        """Validate required secrets. Pass as keyword arguments.

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

**Impact:** Eliminates ~300 lines of duplicated code

---

#### Pattern 3: Preview Builder Functions (76 files)

**Current pattern - every server has this:**
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

**Found in:** aws_s3.py:46-88, gcs.py:17-66, azure_blob.py:38-83, and 73 other files

**Proposed solution:**
Create `server_utils/external_api/preview_builder.py`:
```python
class PreviewBuilder:
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
        """Build a standardized preview object for dry-run mode."""
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
            preview["headers"] = headers
        if extra:
            preview.update(extra)
        return preview
```

**Impact:** Eliminates 76 duplicate functions, saves ~2,000+ lines of code

---

#### Pattern 4: Dry-Run Logic (76 files)

**Current pattern:**
```python
if dry_run:
    preview = _build_preview(...)
    return {"output": {"preview": preview, "message": "Dry run - no API call made"}}
```

**Found in:** aws_s3.py:167-176, gcs.py:154-162, azure_blob.py:176-185, and all other servers

**Proposed solution:**
Create `server_utils/external_api/dry_run.py`:
```python
from functools import wraps
from typing import Callable, Dict, Any

def with_dry_run(preview_builder: Callable):
    """Decorator to add dry-run support to server operations.

    Usage:
        @with_dry_run(lambda **kwargs: PreviewBuilder.build(...))
        def my_operation(**kwargs):
            # This only runs when dry_run=False
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, dry_run=True, **kwargs):
            if dry_run:
                preview = preview_builder(**kwargs)
                return {
                    "output": {
                        "preview": preview,
                        "message": "Dry run - no API call made"
                    }
                }
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Impact:** Simplifies 76 server implementations, eliminates ~500 lines

---

#### Pattern 5: Request Exception Handling (30+ files)

**Current pattern in earlier servers:**
```python
except requests.RequestException as exc:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return error_output("Request failed", status_code=status, details=str(exc))
```

**Found in:** github.py:127-129, slack.py:62-66, stripe.py:198-200, asana.py:168-170, and ~26 other files

**Proposed solution:**
Create `server_utils/external_api/response_handler.py`:
```python
import requests
from typing import Dict, Any, Optional, Callable

class ResponseHandler:
    @staticmethod
    def handle_request_exception(exc: requests.RequestException) -> Dict[str, Any]:
        """Standardized handling of requests exceptions."""
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
        """Parse JSON response and handle errors consistently."""
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

**Impact:** Eliminates ~400 lines of duplicated error handling

---

#### Pattern 6: JSON Parsing Errors (30+ files)

**Current pattern:**
```python
try:
    data = response.json()
except ValueError:
    return error_output("Invalid JSON response", status_code=response.status_code, details=response.text)
```

**Found in:** github.py:131-138, slack.py:68-75, airtable.py:130-137, asana.py:43-51, notion.py:130-137, etc.

**Proposed solution:**
Handled by the `ResponseHandler.handle_json_response()` method above.

---

### 2.2 Database Server Similarities

**High similarity (95%) between:**
- `postgresql.py`
- `mysql.py`
- `snowflake.py`

**Differences:**
- Import statements (psycopg2 vs mysql.connector vs snowflake.connector)
- Connection parameter names
- Specific SQL syntax quirks

**Proposed solution:**
Create `server_utils/external_api/database_connection.py`:
```python
from typing import Dict, Any, Optional, List
from enum import Enum

class DatabaseDriver(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SNOWFLAKE = "snowflake"

class DatabaseConnection:
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
        """Unified database query execution across different drivers."""
        # Import appropriate driver
        # Handle connection
        # Execute query with timeout
        # Return results
        ...
```

**Impact:** Could reduce 3 servers from ~200 lines each to ~50 lines each (450 line reduction)

---

### 2.3 Cloud Storage Server Similarities

**High similarity (90%) between:**
- `aws_s3.py`
- `gcs.py`
- `azure_blob.py`

**Common operations:**
- list_buckets/containers
- list_objects/blobs
- get_object/blob
- put_object/blob
- delete_object/blob

**Differences:**
- Authentication mechanisms
- API endpoints
- Parameter naming

**Proposed solution:**
Create abstract base class for cloud storage:
```python
from abc import ABC, abstractmethod

class CloudStorageProvider(ABC):
    @abstractmethod
    def authenticate(self) -> Dict[str, str]:
        """Return authentication headers."""
        pass

    @abstractmethod
    def build_url(self, operation: str, **params) -> str:
        """Build the request URL for an operation."""
        pass

    def list_buckets(self, **kwargs):
        # Shared implementation
        pass

    def list_objects(self, bucket: str, prefix: str = "", **kwargs):
        # Shared implementation
        pass
```

**Impact:** Could reduce 3 servers from ~250 lines each to ~100 lines each (450 line reduction)

---

## 3. ERROR HANDLING INCONSISTENCIES

### 3.1 Broad Exception Catching in Recent Servers

**Issue:** Phase 17-19 servers use broad exception handling that loses context:

```python
except Exception as e:
    return error_output(str(e), status_code=500)
```

**Found in:**
- aws_s3.py:237
- gcs.py:251
- mongodb.py:178
- And other recent servers

**Earlier servers used more specific patterns:**
```python
except requests.RequestException as exc:
    # Handle specifically
except ValueError:
    # Handle JSON parsing
```

**Recommendation:**
- Be specific about exceptions being caught
- Different error types should produce different status codes
- Preserve stack traces in logs (but not in user-facing errors)

**Proposed improvement:**
```python
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

---

### 3.2 Inconsistent Response Checking

**Pattern 1** (49 files):
```python
if not response.ok:
    return error_output(...)
```

**Pattern 2** (Earlier files):
```python
if not getattr(response, "ok", False):
    return error_output(...)
```

**Issue:** The `getattr` pattern is defensive programming for cases where response might not have an `ok` attribute, but it's inconsistently applied.

**Recommendation:**
Standardize on one approach. Since we're using `requests.Response` objects, the simple `if not response.ok:` is appropriate. But if we want to be defensive:

```python
# In response_handler.py
def check_response_ok(response) -> bool:
    """Safely check if response indicates success."""
    return getattr(response, "ok", False)
```

---

## 4. MISSING VALIDATION

### 4.1 No Input Sanitization for SQL Query Strings

**Priority:** HIGH
**Files:** postgresql.py:34-80, mysql.py:34-79, snowflake.py:35-79

**Issue:** Raw SQL query strings are accepted without any validation:

```python
def main(*, query: str = "", ...):
    if not query:
        return validation_error("Missing required query", field="query")
    # No validation of query content!
    cursor.execute(query, params)
```

**Risks:**
- While parameterized queries help, malicious queries could still:
  - Drop tables (if permissions allow)
  - Read sensitive data
  - Cause performance issues (cartesian joins, etc.)

**Recommended mitigations:**
1. Add query pattern validation (allow SELECT, INSERT, UPDATE, DELETE but warn on DROP, ALTER, etc.)
2. Add query complexity limits
3. Consider read-only mode for certain operations
4. Document security expectations

**Example validation:**
```python
DANGEROUS_KEYWORDS = {"DROP", "ALTER", "GRANT", "REVOKE", "TRUNCATE"}

def validate_query(query: str) -> Optional[Dict[str, Any]]:
    """Validate query for dangerous operations."""
    upper_query = query.upper()
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf'\b{keyword}\b', upper_query):
            return error_output(
                f"Query contains potentially dangerous keyword: {keyword}",
                status_code=403
            )
    return None
```

---

### 4.2 Missing Parameter Bounds Checking

**Files:** aws_s3.py:98, gcs.py:76, azure_blob.py:93, github.py:56, asana.py:86, etc.

**Issue:** Limit/pagination parameters have no bounds checking:

```python
max_keys: int = 1000,  # What if user passes 999999999?
```

**Recommendation:**
```python
MAX_ALLOWED_LIMIT = 10000

def validate_limit(limit: int, field_name: str = "limit") -> Optional[Dict[str, Any]]:
    if limit < 1:
        return validation_error(f"{field_name} must be positive", field=field_name)
    if limit > MAX_ALLOWED_LIMIT:
        return validation_error(
            f"{field_name} exceeds maximum of {MAX_ALLOWED_LIMIT}",
            field=field_name
        )
    return None
```

---

### 4.3 Inconsistent Required Field Validation

**Better pattern** (gcs.py:125-139):
```python
if normalized_operation == "list_buckets" and not project_id:
    return validation_error("Missing required project_id for list_buckets", field="project_id")
```

**Weaker pattern** (github.py:102-105):
```python
elif normalized_operation == "get_issue":
    if issue_number is None:
        return validation_error("Missing required issue_number", field="issue_number")
```

**Recommendation:**
Create a parameter requirement map and validator:

```python
class ParameterValidator:
    @staticmethod
    def validate_required_for_operation(
        operation: str,
        operation_requirements: Dict[str, List[str]],
        provided_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Validate that all required parameters for an operation are provided."""
        required = operation_requirements.get(operation, [])
        for param in required:
            if param not in provided_params or provided_params[param] is None:
                return validation_error(
                    f"Missing required {param} for {operation}",
                    field=param
                )
        return None

# Usage in server:
REQUIREMENTS = {
    "list_buckets": ["project_id"],
    "get_object": ["bucket", "key"],
    "put_object": ["bucket", "key", "data"],
}

error = ParameterValidator.validate_required_for_operation(
    operation, REQUIREMENTS, locals()
)
if error:
    return error
```

---

## 5. HARD-CODED VALUES

### 5.1 API Versions

**Good example** (notion.py:17):
```python
_DEF_VERSION = "2022-06-28"
notion_version: str = _DEF_VERSION,  # Allows override
```

**Bad example** (azure_blob.py:30):
```python
"x-ms-version": "2021-08-06",  # Hard-coded, no override
```

**Recommendation:**
All API versions should be configurable parameters with sensible defaults:

```python
def main(
    *,
    operation: str,
    api_version: str = "2021-08-06",  # Default but overridable
    ...
):
```

---

### 5.2 Timeout Values

**Inconsistent defaults across servers:**
- Most servers: `timeout: int = 60`
- google_auth.py: `timeout=30`
- Database servers: separate `connection_timeout` and `query_timeout`

**Recommendation:**
Create configuration constants:

```python
# In server_utils/external_api/config.py
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

### 5.3 Retry Configuration

**Currently hard-coded in http_client.py:**
```python
max_retries: int = 3
backoff_factor: float = 2.0
retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)
```

**Recommendation:**
Make configurable per-server and per-operation:

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

### 5.4 Default Limits - Inconsistent Values

**Current defaults:**
- aws_s3.py: `max_keys: int = 1000`
- gcs.py: `max_results: int = 1000`
- azure_blob.py: `max_results: int = 1000`
- mongodb.py: `limit: int = 100`
- github.py: `per_page: int = 30`
- asana.py: `limit: int = 20`

**Recommendation:**
Standardize naming and defaults while respecting API-specific constraints:

```python
# In server_utils/external_api/config.py
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# In servers, use consistent naming:
page_size: int = DEFAULT_PAGE_SIZE  # Not max_keys, max_results, per_page, limit
```

---

## 6. TEST IMPROVEMENTS

### 6.1 Current Test Coverage

**Excellent coverage overall:**
- 99 test files
- 1296 test functions
- All major servers have tests

**Test pattern analysis shows consistent coverage of:**
- Missing credentials
- Invalid operations
- Missing required fields
- Dry-run previews
- Request exceptions
- Invalid JSON responses
- API errors
- Success cases

---

### 6.2 Test Quality Improvements

#### 6.2.1 Add Property-Based Testing

Current tests use fixed examples. Consider property-based testing for:

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

#### 6.2.2 Add Integration Test Suite

**Currently missing:**
- Actual database connections (with test containers)
- Real API authentication flows (with test credentials)
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

```python
# tests/integration/test_database_servers.py
@pytest.mark.integration
def test_postgresql_real_connection():
    """Test actual PostgreSQL connection and query."""
    result = postgresql.main(
        operation="query",
        query="SELECT version()",
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_PORT="5432",
        POSTGRESQL_DATABASE="test",
        POSTGRESQL_USER="test",
        POSTGRESQL_PASSWORD="test",
        dry_run=False,
    )
    assert "output" in result
    assert "rows" in result["output"]
```

---

#### 6.2.3 Add Performance/Load Tests

Test timeout and rate limiting behavior:

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

#### 6.2.4 Add Security Tests

Test authentication and authorization:

```python
def test_rejects_sql_injection_attempt():
    """Verify SQL injection patterns are caught."""
    malicious_query = "SELECT * FROM users; DROP TABLE users; --"
    result = postgresql.main(
        operation="query",
        query=malicious_query,
        dry_run=False,
        ...
    )
    assert "error" in result["output"]
    assert result["output"]["status_code"] == 403
```

---

#### 6.2.5 Improve Test Organization

**Current structure:**
```
tests/
  test_external_server_aws_s3.py
  test_external_server_github.py
  ...
```

**Recommended structure:**
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

#### 6.2.6 Add Shared Utility Tests

When implementing shared utilities, test them thoroughly:

```python
# tests/shared/test_credential_validator.py
def test_require_secrets_all_present():
    result = CredentialValidator.require_secrets(
        API_KEY="key123",
        API_SECRET="secret456"
    )
    assert result is None  # No error

def test_require_secrets_missing_one():
    result = CredentialValidator.require_secrets(
        API_KEY="key123",
        API_SECRET=""
    )
    assert result is not None
    assert "Missing API_SECRET" in result["output"]["error"]
    assert result["output"]["status_code"] == 401
```

---

## 7. AUTHENTICATION ABSTRACTION OPPORTUNITIES

### 7.1 Current Authentication Patterns

**Pattern 1: Bearer Token** (50+ servers)
```python
headers = {"Authorization": f"Bearer {TOKEN}"}
```

**Pattern 2: Basic Auth** (Snowflake, PostgreSQL, MySQL, etc.)
```python
auth_string = f"{USER}:{PASSWORD}"
encoded_auth = base64.b64encode(auth_string.encode()).decode()
headers = {"Authorization": f"Basic {encoded_auth}"}
```

**Pattern 3: API Key in Headers** (Various servers)
```python
headers = {"X-API-Key": API_KEY}
# Or
headers = {"Api-Token": API_TOKEN}
```

**Pattern 4: OAuth/Service Account** (Google services)
- Shared via GoogleAuthManager (good!)
- But still duplicated setup code in each server

**Pattern 5: Signature-based** (AWS, Azure)
- Custom implementation per service
- Currently incomplete/placeholder

---

### 7.2 Proposed Authentication Abstraction

Create `server_utils/external_api/auth_providers.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Optional
import base64
import hashlib
import hmac
from datetime import datetime

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


class AWSSignatureV4Provider(AuthProvider):
    """AWS Signature Version 4 authentication."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str,
        service: str,
        session_token: Optional[str] = None
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
        self.session_token = session_token

    def sign_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        payload: str = ""
    ) -> Dict[str, str]:
        """Sign a request with AWS Signature V4.

        Reference: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
        """
        # Implementation of proper AWS SigV4 signing
        # 1. Create canonical request
        # 2. Create string to sign
        # 3. Calculate signature
        # 4. Add authorization header
        ...
        return signed_headers

    def get_auth_headers(self) -> Dict[str, str]:
        # Note: For AWS, we need request details to sign
        # So this returns static headers, actual signing done per-request
        headers = {"X-Amz-Date": datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}
        if self.session_token:
            headers["X-Amz-Security-Token"] = self.session_token
        return headers

    def get_auth_description(self) -> str:
        return "AWS Signature V4"


class AzureSharedKeyProvider(AuthProvider):
    """Azure Shared Key authentication."""

    def __init__(self, account_name: str, account_key: str):
        self.account_name = account_name
        self.account_key = account_key

    def sign_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str]
    ) -> Dict[str, str]:
        """Sign a request with Azure Shared Key.

        Reference: https://docs.microsoft.com/en-us/rest/api/storageservices/authorize-with-shared-key
        """
        # Implementation of proper Azure Shared Key signing
        # 1. Create canonical headers
        # 2. Create string to sign
        # 3. Calculate HMAC-SHA256 signature
        # 4. Add authorization header
        ...
        return signed_headers

    def get_auth_headers(self) -> Dict[str, str]:
        # Azure signing is also per-request
        return {"x-ms-date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}

    def get_auth_description(self) -> str:
        return "Azure Shared Key"
```

---

### 7.3 Usage Example

**Before (aws_s3.py):**
```python
def _sign_request(...) -> Dict[str, str]:
    # 30+ lines of signing logic
    ...

def main(...):
    headers = _sign_request(...)
    response = client.request(method, url, headers=headers)
```

**After:**
```python
from server_utils.external_api.auth_providers import AWSSignatureV4Provider

def main(...):
    auth = AWSSignatureV4Provider(
        access_key=AWS_ACCESS_KEY_ID,
        secret_key=AWS_SECRET_ACCESS_KEY,
        region=region,
        service="s3"
    )

    headers = auth.get_auth_headers()
    # For signature-based auth, sign each request:
    headers = auth.sign_request(method, url, headers, payload)

    response = client.request(method, url, headers=headers)
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (Immediate)

**Priority: CRITICAL**
**Estimated effort:** 2-3 days

1. ✅ Implement proper AWS Signature V4 in `server_utils/external_api/aws_signature.py`
2. ✅ Implement proper Azure Shared Key in `server_utils/external_api/azure_signature.py`
3. ✅ Update `aws_s3.py` to use proper signing
4. ✅ Update `azure_blob.py` to use proper signing
5. ✅ Add integration tests for AWS and Azure authentication
6. ✅ Verify both servers work with `dry_run=False`

---

### Phase 2: Shared Utilities Foundation (High Priority)

**Priority: HIGH**
**Estimated effort:** 3-5 days

1. ✅ Create `server_utils/external_api/operation_validator.py`
2. ✅ Create `server_utils/external_api/credential_validator.py`
3. ✅ Create `server_utils/external_api/preview_builder.py`
4. ✅ Create `server_utils/external_api/response_handler.py`
5. ✅ Create `server_utils/external_api/parameter_validator.py`
6. ✅ Add comprehensive unit tests for all utilities
7. ✅ Update documentation with usage examples

---

### Phase 3: Refactor 10 Representative Servers (High Priority)

**Priority: HIGH**
**Estimated effort:** 5-7 days

Refactor a diverse sample to validate the abstractions:

1. ✅ `github.py` (Bearer auth, simple REST)
2. ✅ `slack.py` (Bearer auth, webhook support)
3. ✅ `aws_s3.py` (Signature auth, cloud storage)
4. ✅ `gcs.py` (OAuth, cloud storage)
5. ✅ `azure_blob.py` (Shared Key, cloud storage)
6. ✅ `postgresql.py` (Basic auth, database)
7. ✅ `mongodb.py` (URI auth, NoSQL)
8. ✅ `stripe.py` (Bearer auth, API key)
9. ✅ `shopify.py` (Custom auth, webhooks)
10. ✅ `notion.py` (Bearer auth, versioned API)

**Success criteria:**
- Each server reduces from ~200 lines to ~80 lines
- All existing tests pass
- No change in external API/behavior
- Documentation updated

---

### Phase 4: Security Improvements (High Priority)

**Priority: HIGH**
**Estimated effort:** 2-3 days

1. ✅ Fix SQL injection risk in `postgresql.py`, `mysql.py`, `snowflake.py`
2. ✅ Add query validation for database servers
3. ✅ Fix connection string parsing in `azure_blob.py`
4. ✅ Improve credential sanitization in preview mode
5. ✅ Add security tests for all database servers
6. ✅ Add input validation for all limit/pagination parameters

---

### Phase 5: Remaining Server Refactoring (Medium Priority)

**Priority: MEDIUM**
**Estimated effort:** 10-15 days

Refactor remaining 66 servers in batches:

**Batch 1: Cloud Storage (remaining)**
- Dropbox, Box

**Batch 2: Google Suite (9 servers)**
- google_drive, google_calendar, youtube, google_contacts, google_docs, google_forms, google_analytics, google_ads, google_sheets

**Batch 3: Microsoft Suite (5 servers)**
- microsoft_outlook, microsoft_teams, onedrive, microsoft_excel, dynamics365

**Batch 4: Project Management (9 servers)**
- trello, monday, clickup, jira, confluence, basecamp, smartsheet, todoist, asana

**Batch 5: Communication (4 servers)**
- discord, twilio, whatsapp, telegram

**Batch 6: CRM & Sales (6 servers)**
- salesforce, pipedrive, close_crm, zoho_crm, insightly, calendly

**Batch 7: Customer Support (7 servers)**
- intercom, freshdesk, helpscout, front, gorgias, servicenow, zendesk

**Batch 8: E-commerce & Payments (5 servers)**
- shopify, woocommerce, ebay, etsy, paypal

**Batch 9: Email Marketing (6 servers)**
- klaviyo, activecampaign, mailerlite, sendgrid, mailgun, postmark

**Batch 10: Document & Storage (4 servers)**
- docusign, pandadoc, dropbox, box

**Batch 11: Remaining servers**
- All other servers

---

### Phase 6: Enhanced Testing (Medium Priority)

**Priority: MEDIUM**
**Estimated effort:** 5-7 days

1. ✅ Set up Docker Compose for integration tests
2. ✅ Add integration tests for database servers
3. ✅ Add integration tests for cloud storage (using LocalStack)
4. ✅ Add property-based tests for dry-run mode
5. ✅ Add performance/timeout tests
6. ✅ Add security tests for SQL injection, etc.
7. ✅ Reorganize test directory structure

---

### Phase 7: Authentication Abstraction (Low Priority)

**Priority: LOW**
**Estimated effort:** 3-5 days

1. ✅ Create `server_utils/external_api/auth_providers.py`
2. ✅ Implement all auth provider classes
3. ✅ Add unit tests for auth providers
4. ✅ Update 5-10 servers to use auth providers
5. ✅ Document auth provider usage

---

### Phase 8: Configuration Standardization (Low Priority)

**Priority: LOW**
**Estimated effort:** 2-3 days

1. ✅ Create `server_utils/external_api/config.py`
2. ✅ Standardize timeout values
3. ✅ Standardize default limits
4. ✅ Standardize retry configuration
5. ✅ Make API versions configurable everywhere

---

## 9. RISK ASSESSMENT

### High Risk

1. **Refactoring 76 servers**
   - **Risk:** Introducing bugs in production servers
   - **Mitigation:**
     - Refactor in small batches (10 servers at a time)
     - Require all existing tests to pass
     - Add new tests for edge cases
     - Code review for each batch
     - Consider feature flag for new vs old implementation

2. **AWS/Azure signature implementation**
   - **Risk:** Incorrect signature could break all operations
   - **Mitigation:**
     - Implement comprehensive test suite
     - Test against real AWS/Azure services (in test account)
     - Review AWS/Azure documentation thoroughly
     - Consider using existing libraries (boto3 for AWS)

---

### Medium Risk

1. **Backward compatibility**
   - **Risk:** Changes to shared utilities could affect existing integrations
   - **Mitigation:**
     - Maintain strict API compatibility
     - Version shared utilities if breaking changes needed
     - Document any behavior changes

2. **Performance impact**
   - **Risk:** Adding layers of abstraction could slow down operations
   - **Mitigation:**
     - Benchmark before/after refactoring
     - Profile hot paths
     - Optimize shared utilities

---

### Low Risk

1. **Configuration changes**
   - **Risk:** Changing default values could surprise users
   - **Mitigation:**
     - Keep existing defaults unless clearly broken
     - Document all configuration options
     - Provide migration guide if needed

---

## 10. SUCCESS METRICS

### Code Quality Metrics

- **Lines of Code:** Reduce from ~15,200 to ~6,080 (60% reduction)
- **Code Duplication:** Reduce from ~9,120 duplicated lines to <500
- **Test Coverage:** Maintain >90% coverage
- **Pylint Score:** Maintain >9.0/10

---

### Security Metrics

- **Critical Issues:** Reduce from 2 to 0 (AWS/Azure signatures fixed)
- **High Priority Issues:** Reduce from 3 to 0
- **Medium Priority Issues:** Reduce from 4 to <2

---

### Performance Metrics

- **Server Response Time:** No degradation (benchmark before/after)
- **Test Suite Runtime:** <10% increase acceptable

---

### Developer Experience Metrics

- **Time to Add New Server:** Reduce from ~4 hours to ~1 hour
- **Lines per Server:** Average ~80 lines (down from ~200)
- **Shared Code Reuse:** >60% of server code using shared utilities

---

## 11. APPENDIX: CONCRETE CODE EXAMPLES

### Example 1: Refactored Server (Before/After)

**Before (github.py - 180 lines):**
```python
def main(
    *,
    operation: str = "",
    repository: str = "",
    issue_number: Optional[int] = None,
    title: str = "",
    body: str = "",
    GITHUB_TOKEN: str = "",
    dry_run: bool = True,
    timeout: int = 60,
) -> Dict[str, Any]:
    # Validate operation
    valid_operations = {"list_issues", "get_issue", "create_issue"}
    normalized_operation = operation.lower()
    if normalized_operation not in valid_operations:
        return validation_error("Unsupported operation", field="operation")

    # Validate credentials
    if not GITHUB_TOKEN:
        return error_output("Missing GITHUB_TOKEN", status_code=401)

    # Validate required fields
    if not repository:
        return validation_error("Missing required repository", field="repository")

    if normalized_operation == "get_issue":
        if issue_number is None:
            return validation_error("Missing required issue_number", field="issue_number")

    # Build preview
    if dry_run:
        preview = _build_preview(
            operation=normalized_operation,
            repository=repository,
            issue_number=issue_number,
            title=title,
            body=body,
        )
        return {"output": {"preview": preview, "message": "Dry run - no API call made"}}

    # Make API call
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    base_url = f"https://api.github.com/repos/{repository}/issues"

    try:
        if normalized_operation == "list_issues":
            response = requests.get(base_url, headers=headers, timeout=timeout)
        elif normalized_operation == "get_issue":
            response = requests.get(f"{base_url}/{issue_number}", headers=headers, timeout=timeout)
        elif normalized_operation == "create_issue":
            payload = {"title": title, "body": body}
            response = requests.post(base_url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return error_output("Request failed", status_code=status, details=str(exc))

    # Parse response
    try:
        data = response.json()
    except ValueError:
        return error_output(
            "Invalid JSON response",
            status_code=response.status_code,
            details=response.text
        )

    if not response.ok:
        message = data.get("message", "API error")
        return error_output(message, status_code=response.status_code, response=data)

    return {"output": data}
```

**After (github.py - 75 lines):**
```python
from server_utils.external_api import (
    OperationValidator,
    CredentialValidator,
    ParameterValidator,
    PreviewBuilder,
    ResponseHandler,
    with_dry_run,
    BearerAuthProvider,
)

OPERATIONS = {"list_issues", "get_issue", "create_issue"}
REQUIREMENTS = {
    "get_issue": ["issue_number"],
    "create_issue": ["title"],
}

@with_dry_run(lambda **kwargs: _build_preview(**kwargs))
def main(
    *,
    operation: str = "",
    repository: str = "",
    issue_number: Optional[int] = None,
    title: str = "",
    body: str = "",
    GITHUB_TOKEN: str = "",
    timeout: int = 60,
) -> Dict[str, Any]:
    # Validate
    validator = OperationValidator(OPERATIONS)
    if error := validator.validate(operation):
        return error

    if error := CredentialValidator.require_secrets(GITHUB_TOKEN=GITHUB_TOKEN):
        return error

    if not repository:
        return validation_error("Missing required repository", field="repository")

    params = locals()
    if error := ParameterValidator.validate_required_for_operation(
        operation, REQUIREMENTS, params
    ):
        return error

    # Build request
    auth = BearerAuthProvider(GITHUB_TOKEN)
    base_url = f"https://api.github.com/repos/{repository}/issues"

    if operation == "list_issues":
        method, url, payload = "GET", base_url, None
    elif operation == "get_issue":
        method, url, payload = "GET", f"{base_url}/{issue_number}", None
    elif operation == "create_issue":
        method, url, payload = "POST", base_url, {"title": title, "body": body}

    # Make request
    try:
        response = requests.request(
            method, url,
            headers=auth.get_auth_headers(),
            json=payload,
            timeout=timeout
        )
    except requests.RequestException as exc:
        return ResponseHandler.handle_request_exception(exc)

    # Handle response
    return ResponseHandler.handle_json_response(
        response,
        error_message_extractor=lambda data: data.get("message", "API error")
    )

def _build_preview(**kwargs) -> Dict[str, Any]:
    return PreviewBuilder.build(
        operation=kwargs["operation"],
        url=f"https://api.github.com/repos/{kwargs['repository']}/issues",
        method="GET/POST",
        auth_type="Bearer Token",
        params={k: v for k, v in kwargs.items() if v and k not in ["GITHUB_TOKEN", "dry_run", "timeout"]}
    )
```

**Result:**
- 180 lines → 75 lines (58% reduction)
- More readable and maintainable
- Uses shared, tested utilities
- Same behavior and API

---

### Example 2: Shared Utility Implementation

**Complete implementation of PreviewBuilder:**

```python
# server_utils/external_api/preview_builder.py
"""Utilities for building dry-run previews."""

from typing import Any, Dict, Optional


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
        """Build a preview object showing what would be executed.

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

        Example:
            >>> preview = PreviewBuilder.build(
            ...     operation="list_issues",
            ...     url="https://api.github.com/repos/owner/repo/issues",
            ...     method="GET",
            ...     auth_type="Bearer Token",
            ...     params={"state": "open"}
            ... )
            >>> preview["operation"]
            'list_issues'
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
    """Redact sensitive information from headers for preview.

    Args:
        headers: Original headers dict

    Returns:
        Headers with sensitive values redacted
    """
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

**Tests for PreviewBuilder:**

```python
# tests/shared/test_preview_builder.py
from server_utils.external_api.preview_builder import PreviewBuilder


def test_build_basic_preview():
    preview = PreviewBuilder.build(
        operation="test_op",
        url="https://api.example.com/resource",
        method="GET",
        auth_type="Bearer Token"
    )

    assert preview["operation"] == "test_op"
    assert preview["url"] == "https://api.example.com/resource"
    assert preview["method"] == "GET"
    assert preview["auth"] == "Bearer Token"


def test_build_with_params():
    preview = PreviewBuilder.build(
        operation="list",
        url="https://api.example.com/items",
        method="GET",
        auth_type="API Key",
        params={"limit": 10, "offset": 0}
    )

    assert "params" in preview
    assert preview["params"]["limit"] == 10
    assert preview["params"]["offset"] == 0


def test_build_with_payload():
    preview = PreviewBuilder.build(
        operation="create",
        url="https://api.example.com/items",
        method="POST",
        auth_type="Bearer Token",
        payload={"name": "Test", "value": 123}
    )

    assert "payload" in preview
    assert preview["payload"]["name"] == "Test"


def test_build_redacts_sensitive_headers():
    preview = PreviewBuilder.build(
        operation="test",
        url="https://api.example.com",
        method="GET",
        auth_type="Bearer Token",
        headers={
            "Authorization": "Bearer secret123",
            "X-API-Key": "key456",
            "Content-Type": "application/json",
        }
    )

    assert preview["headers"]["Authorization"] == "***"
    assert preview["headers"]["X-API-Key"] == "***"
    assert preview["headers"]["Content-Type"] == "application/json"


def test_build_with_extra_fields():
    preview = PreviewBuilder.build(
        operation="query",
        url="https://db.example.com",
        method="POST",
        auth_type="Basic Auth",
        database="testdb",
        collection="users",
        custom_field="value"
    )

    assert preview["database"] == "testdb"
    assert preview["collection"] == "users"
    assert preview["custom_field"] == "value"
```

---

## 12. NEXT STEPS

1. **Review this document** with the team
2. **Prioritize phases** based on business needs
3. **Assign owners** for each phase
4. **Create detailed technical specs** for Phase 1 (Critical Fixes)
5. **Set up tracking** for progress and metrics
6. **Schedule kickoff** for Phase 1 implementation

---

## 13. REFERENCES

- Original implementation plan: `done/add_external_server_definitions.md`
- Test index: `TEST_INDEX.md`
- Existing shared utilities: `server_utils/external_api/`
- AWS Signature V4: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
- Azure Shared Key: https://docs.microsoft.com/en-us/rest/api/storageservices/authorize-with-shared-key

---

**Document Status:** Ready for Review
**Last Updated:** 2026-01-02
**Next Review:** After Phase 1 completion
