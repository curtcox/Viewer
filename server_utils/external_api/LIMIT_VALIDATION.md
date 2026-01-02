# Limit Validation for External API Servers

This document describes the limit validation system implemented for external API servers to enforce per-service pagination and result limit constraints.

## Overview

External APIs enforce maximum limits on pagination parameters (e.g., `limit`, `max_keys`, `per_page`, `max_results`). This validation system ensures that:

1. **Early validation**: Limits are validated at the server entrypoint before any processing
2. **Clear error messages**: Users receive helpful errors when exceeding limits
3. **Transparency**: Dry-run previews show the enforced limits and their rationale
4. **Service-specific constraints**: Each API's documented limits are enforced

## Architecture

### Core Components

1. **`limit_validator.py`**: Shared validation utilities and service-specific constants
2. **`validate_limit()`**: Main validation function used by all servers
3. **`get_limit_info()`**: Generates limit constraint information for previews
4. **`validate_pagination_params()`**: Validates multiple pagination parameters together

### Service-Specific Constants

Each external API has a documented maximum limit constant:

```python
# Cloud Storage
AWS_S3_MAX_KEYS = 1000  # AWS S3 API maximum
GCS_MAX_RESULTS = 1000  # Google Cloud Storage maximum
AZURE_BLOB_MAX_RESULTS = 5000  # Azure Blob Storage maximum

# Version Control
GITHUB_MAX_PER_PAGE = 100  # GitHub API maximum
GITLAB_MAX_PER_PAGE = 100  # GitLab API maximum

# CRM & Sales
SALESFORCE_MAX_LIMIT = 2000  # Salesforce SOQL maximum
HUBSPOT_MAX_LIMIT = 100  # HubSpot API maximum

# ... and many more
```

See `limit_validator.py` for the complete list with documentation references.

## Usage Pattern

### 1. Import Validation Utilities

```python
from server_utils.external_api.limit_validator import (
    AWS_S3_MAX_KEYS,  # Service-specific constant
    get_limit_info,
    validate_limit,
)
```

### 2. Validate at Entrypoint

Add validation immediately after credential validation, before any other processing:

```python
def main(
    *,
    operation: str = "list_objects",
    max_keys: int = 1000,
    AWS_ACCESS_KEY_ID: str = "",
    AWS_SECRET_ACCESS_KEY: str = "",
    dry_run: bool = True,
    ...
) -> Dict[str, Any]:
    # ... credential validation ...

    # Validate limit parameter (max_keys)
    # AWS S3 API enforces a maximum of 1000 keys per list operation
    if error := validate_limit(max_keys, AWS_S3_MAX_KEYS, "max_keys"):
        return error

    # ... rest of implementation ...
```

### 3. Include Limit Info in Previews

Update the preview builder to accept the limit parameter and include constraint information:

```python
def _build_preview(
    *,
    operation: str,
    # ... other params ...
    max_keys: Optional[int] = None,
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        # ... other fields ...
    }

    # Include limit constraint information for operations that use it
    if max_keys is not None and operation == "list_objects":
        preview["limit_constraint"] = get_limit_info(max_keys, AWS_S3_MAX_KEYS, "max_keys")

    return preview
```

### 4. Pass Limit to Preview

When returning dry-run previews, pass the limit parameter:

```python
if dry_run:
    return {
        "output": _build_preview(
            operation=normalized_operation,
            # ... other args ...
            max_keys=max_keys if normalized_operation == "list_objects" else None,
        )
    }
```

## Error Response Format

When validation fails, users receive a structured error with full context:

```json
{
  "output": {
    "error": {
      "message": "max_keys exceeds maximum allowed value of 1000",
      "type": "validation_error",
      "details": {
        "field": "max_keys",
        "provided": 2000,
        "maximum": 1000,
        "minimum": 1,
        "rationale": "External API enforces max_keys <= 1000"
      }
    },
    "content_type": "application/json"
  }
}
```

## Preview Response Format

Dry-run responses include limit constraint information for transparency:

```json
{
  "output": {
    "operation": "list_objects",
    "url": "https://bucket.s3.us-east-1.amazonaws.com/",
    "method": "GET",
    "auth": "AWS Signature V4",
    "params": {"max-keys": "500"},
    "limit_constraint": {
      "parameter": "max_keys",
      "current": 500,
      "maximum": 1000,
      "status": "valid",
      "constraint_source": "external_api_documentation"
    }
  }
}
```

This allows users to see:
- What limit is being enforced
- The current value they provided
- The maximum allowed value
- Whether their value is valid
- That the constraint comes from the external API's documentation

## Validation Rules

### Minimum Value

By default, limits must be >= 1:

```python
validate_limit(limit=0, max_allowed=100, "limit")
# Returns error: "limit must be at least 1"
```

Custom minimum values can be specified:

```python
validate_limit(limit=5, max_allowed=100, "limit", min_value=10)
# Returns error: "limit must be at least 10"
```

### Maximum Value

Limits must not exceed the service-specific maximum:

```python
validate_limit(limit=200, max_allowed=100, "limit")
# Returns error: "limit exceeds maximum allowed value of 100"
```

### Pagination Parameters

Multiple pagination parameters can be validated together:

```python
error = validate_pagination_params(
    limit=50,
    offset=0,
    page=1,
    max_allowed=100
)
# Returns None (all valid)
```

## Testing

Comprehensive tests are provided in `tests/test_limit_validator.py`:

- **Unit tests**: Test validation logic, error messages, and edge cases
- **Integration tests**: Test with actual server definitions
- **Preview tests**: Verify limit constraint info appears in previews

Run tests:

```bash
uv run pytest tests/test_limit_validator.py -v
```

## Implementation Status

### Completed Servers

1. ✅ **aws_s3.py** - Uses `max_keys` parameter (AWS S3 max: 1000)
2. ✅ **github.py** - Uses `per_page` parameter (GitHub max: 100)
3. ✅ **mongodb.py** - Uses `limit` parameter (MongoDB max: 10000)

### Remaining Servers (35 total)

Servers with limit/pagination parameters that need validation added:

**Cloud Storage:**
- gcs.py (max_results)
- azure_blob.py (max_results)
- dropbox.py (limit)
- box.py (limit)

**Version Control & PM:**
- gitlab.py (per_page)
- asana.py (limit)

**Communication:**
- discord.py (limit)
- telegram.py (limit)
- twilio.py (page_size)
- zoom.py (page_size)

**CRM & Sales:**
- hubspot.py (limit)
- pipedrive.py (limit)
- zoho_crm.py (per_page)
- close_crm.py (limit)

**E-commerce:**
- shopify.py (limit)
- woocommerce.py (per_page)
- stripe.py (limit)
- etsy.py (limit)
- ebay.py (limit)
- squarespace.py (limit)

**Email & Marketing:**
- gmail.py (max_results)
- typeform.py (page_size)
- jotform.py (limit)

**Document & Forms:**
- google_drive.py (page_size)
- google_calendar.py (max_results)
- google_contacts.py (max_results)
- youtube.py (max_results)

**Design & Collaboration:**
- miro.py (limit)
- coda.py (limit)

**Website Builders:**
- wix.py (page_size)
- wordpress.py (per_page)

**Databases:**
- bigquery.py (max_results)
- pymongo_pool.py (limit)

**Social & Ads:**
- meta_ads.py (limit)

**Other:**
- ai_assist.py (limit)
- parseur.py (limit)

### Migration Guide

For each remaining server, follow the pattern in `LIMIT_VALIDATION.md` (this file).

The changes are minimal and follow a consistent pattern:
1. Add 1 import line
2. Add 3 lines of validation code
3. Update preview builder signature (1 line)
4. Add 2 lines in preview builder
5. Update preview call (1 line)

**Total**: ~8 lines of code per server

## API Documentation References

All maximum limits are derived from official API documentation:

- **AWS S3**: https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html
- **GitHub**: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- **Google Cloud Storage**: https://cloud.google.com/storage/docs/json_api/v1/objects/list
- **Azure Blob Storage**: https://docs.microsoft.com/en-us/rest/api/storageservices/list-blobs
- ... (see `limit_validator.py` comments for complete references)

## Benefits

1. **Prevents API errors**: Validates limits before making requests
2. **Clear user feedback**: Detailed error messages explain constraints
3. **Transparency**: Dry-run mode shows enforced limits
4. **Consistency**: Same validation pattern across all servers
5. **Maintainability**: Centralized constants make updates easy
6. **Documentation**: Limits are self-documenting in code

## Future Enhancements

Potential improvements for future iterations:

1. **Dynamic limit discovery**: Query API for current limits
2. **Rate limit integration**: Combine with rate limiting system
3. **Soft limits**: Warn but don't fail for near-limit values
4. **Limit negotiation**: Auto-adjust limits based on API responses
5. **Historical tracking**: Track limit changes over time
6. **Custom limits**: Allow users to set stricter limits per deployment

## Questions & Support

For questions about limit validation:

1. Check this documentation
2. See examples in implemented servers (aws_s3.py, github.py, mongodb.py)
3. Review tests in `tests/test_limit_validator.py`
4. Consult the external API's official documentation

## Related Files

- `server_utils/external_api/limit_validator.py` - Core implementation
- `server_utils/external_api/error_response.py` - Error formatting
- `tests/test_limit_validator.py` - Test suite
- `todo/external_servers_followup.md` - Original review findings
