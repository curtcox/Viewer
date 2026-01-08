# Structural Changes to Reduce Code Complexity

This document proposes concrete structural changes to reduce cyclomatic complexity in the codebase, favoring simplicity over backward compatibility.

## Progress

- ✅ Phase 1: Added structural Pylint checks for complexity gates (max branches/statements/locals/args, McCabe). (Updated `.pylintrc`.)
- ✅ Phase 1: Extracted duplicate endpoint maps to module-level constants for Dropbox.
- ✅ Phase 2: Added shared `OperationDefinition`/`validate_and_build_payload` helper and migrated Dropbox, Telegram, and Salesforce to dispatch tables.
- ✅ Phase 3: Added shared `execute_json_request` helper and migrated Dropbox, Telegram, and Salesforce to use it.
- ✅ Phase 4: Migrated xero.py (complexity 34→15, reduced by 19 branches)
- ✅ Phase 5: Migrated docusign.py (complexity 30→9, reduced by 21 branches)
- ✅ Phase 6: Migrated linkedin_ads.py (complexity 28→9, reduced by 19 branches)
- ✅ Phase 7: Migrated meta_ads.py (complexity 33→13, reduced by 20 branches)
- ✅ Phase 8: Migrated woocommerce.py (complexity 33→10, reduced by 23 branches)
- ✅ Phase 9: Migrated freshbooks.py, docparser.py, and onedrive.py to dispatch tables and shared executor.
- ✅ Phase 10: Migrated servicenow.py, helpscout.py, etsy.py, figma.py, klaviyo.py, and quickbooks.py to dispatch tables and shared executor.
- ✅ Phase 11: Migrated mailchimp.py, mailerlite.py, and zoho_crm.py to dispatch tables and shared executor.
- ✅ Phase 12: Migrated calendly.py, pipedrive.py, gitlab.py, wordpress.py, and webflow.py to dispatch tables and shared executor.
- ✅ Phase 13: Migrated google_ads.py, google_contacts.py, google_forms.py, and pandadoc.py to dispatch tables and shared executor.
- ⏳ Remaining servers: 50+ servers with 10+ branches still need migration

## Summary of Improvements

Successfully migrated **20 high-complexity external API servers** to use dispatch table pattern:

| Server | Before | After | Reduction | Status |
|--------|--------|-------|-----------|--------|
| dropbox.py | 35 | ~15 | -20 | ✅ Completed (Phase 2) |
| telegram.py | 34 | ~10 | -24 | ✅ Completed (Phase 2) |
| salesforce.py | 34 | ~12 | -22 | ✅ Completed (Phase 2) |
| **xero.py** | 34 | 15 | -19 | ✅ Completed (Phase 4) |
| **docusign.py** | 30 | 9 | -21 | ✅ Completed (Phase 5) |
| **linkedin_ads.py** | 28 | 9 | -19 | ✅ Completed (Phase 6) |
| **meta_ads.py** | 33 | 13 | -20 | ✅ Completed (Phase 7) |
| **woocommerce.py** | 33 | 10 | -23 | ✅ Completed (Phase 8) |
| **freshbooks.py** | 33 | TBD | TBD | ✅ Completed (Phase 9) |
| **docparser.py** | 32 | TBD | TBD | ✅ Completed (Phase 9) |
| **onedrive.py** | 32 | TBD | TBD | ✅ Completed (Phase 9) |
| **servicenow.py** | 31 | TBD | TBD | ✅ Completed (Phase 10) |
| **helpscout.py** | 31 | TBD | TBD | ✅ Completed (Phase 10) |
| **etsy.py** | 31 | TBD | TBD | ✅ Completed (Phase 10) |
| **figma.py** | 32 | TBD | TBD | ✅ Completed (Phase 10) |
| **klaviyo.py** | 31 | TBD | TBD | ✅ Completed (Phase 10) |
| **quickbooks.py** | 32 | TBD | TBD | ✅ Completed (Phase 10) |
| **mailchimp.py** | TBD | TBD | TBD | ✅ Completed (Phase 11) |
| **mailerlite.py** | TBD | TBD | TBD | ✅ Completed (Phase 11) |
| **zoho_crm.py** | TBD | TBD | TBD | ✅ Completed (Phase 11) |
| **calendly.py** | TBD | TBD | TBD | ✅ Completed (Phase 12) |
| **pipedrive.py** | TBD | TBD | TBD | ✅ Completed (Phase 12) |
| **gitlab.py** | TBD | TBD | TBD | ✅ Completed (Phase 12) |
| **wordpress.py** | TBD | TBD | TBD | ✅ Completed (Phase 12) |
| **webflow.py** | TBD | TBD | TBD | ✅ Completed (Phase 12) |
| **google_ads.py** | TBD | TBD | TBD | ✅ Completed (Phase 13) |
| **google_contacts.py** | TBD | TBD | TBD | ✅ Completed (Phase 13) |
| **google_forms.py** | TBD | TBD | TBD | ✅ Completed (Phase 13) |
| **pandadoc.py** | TBD | TBD | TBD | ✅ Completed (Phase 13) |

**Total complexity reduction: 168+ branches eliminated across 24 servers (pending updated counts for Phase 11-13)**

### Pattern Applied

Each migrated server now follows this simplified structure:

1. **Operation definitions** - Declarative dispatch table with `OperationDefinition` objects
2. **Validation** - Automated via `validate_and_build_payload()` helper
3. **Request execution** - Standardized via `execute_json_request()` helper
4. **No more if-elif chains** - Replaced with data-driven configuration

### Benefits Achieved

- **Reduced duplication**: Endpoint maps defined once, not twice
- **Lower complexity**: Average reduction of ~20 branches per server
- **Easier to test**: Each operation definition independently testable
- **Faster to extend**: New operations require 3-5 lines instead of 30+
- **More maintainable**: Clear separation of concerns

## Current State

The Radon analysis shows 25 server definitions with E-grade complexity (31-35):

| Complexity | Count | Examples |
|------------|-------|----------|
| 35 | 1 | dropbox.py |
| 34 | 5 | xero.py, telegram.py, linkedin_ads.py, docusign.py, salesforce.py |
| 33 | 1 | freshbooks.py |
| 32 | 4 | docparser.py, onedrive.py, mongodb.py, squarespace.py |
| 31 | 5 | aws_s3.py and others |

Note: freshbooks.py, docparser.py, and onedrive.py were migrated in Phase 9; servicenow.py, helpscout.py, etsy.py, figma.py, klaviyo.py, and quickbooks.py were migrated in Phase 10. Refresh the Radon analysis counts when convenient.

**Root cause**: All complexity stems from the same anti-pattern—large if-elif chains in `main()` functions that dispatch operations.

---

## Proposed Changes

### 1. Eliminate Duplicate Endpoint Maps

**Problem**: Every server defines the same endpoint map twice—once in `_build_preview()` and once in `main()`.

**Example from dropbox.py**:
```python
def _build_preview(...):
    endpoint_map = {  # First definition
        "list_folder": "files/list_folder",
        "download": "files/download",
        ...
    }

def main(...):
    endpoint_map = {  # Duplicate definition
        "list_folder": "files/list_folder",
        "download": "files/download",
        ...
    }
```

**Solution**: Extract to module-level constant.

```python
_ENDPOINT_MAP = {
    "list_folder": "files/list_folder",
    "download": "files/download",
    ...
}

def _build_preview(...):
    endpoint = _ENDPOINT_MAP.get(operation, operation)
    ...

def main(...):
    endpoint = _ENDPOINT_MAP.get(operation, operation)
    ...
```

**Impact**: Reduces lines by 10-15 per server (250-375 lines total across 25 servers).

---

### 2. Replace If-Elif Chains with Operation Dispatch Tables

**Problem**: Each server has 10-15 branches like this:

```python
if operation == "list_folder":
    payload = {"path": path}
elif operation == "download":
    if not path:
        return validation_error(...)
    payload = {"path": path}
elif operation == "upload":
    if not path:
        return validation_error(...)
    if not content:
        return validation_error(...)
    payload = {"path": path, "content": content}
# ... 10 more branches
```

**Solution**: Use declarative operation definitions.

```python
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class Operation:
    required: tuple[str, ...] = ()
    payload_builder: Optional[Callable] = None

_OPERATIONS = {
    "list_folder": Operation(
        payload_builder=lambda path, **_: {"path": path or ""}
    ),
    "download": Operation(
        required=("path",),
        payload_builder=lambda path, **_: {"path": path}
    ),
    "upload": Operation(
        required=("path", "content"),
        payload_builder=lambda path, content, mode, autorename, mute, **_: {
            "path": path, "mode": mode, "autorename": autorename, "mute": mute
        }
    ),
}

def _validate_and_build_payload(operation: str, **kwargs) -> dict | tuple[str, str]:
    """Returns payload dict or (error_message, field_name) tuple."""
    op = _OPERATIONS.get(operation)
    if not op:
        return ("Unsupported operation", "operation")

    for field in op.required:
        if not kwargs.get(field):
            return (f"Missing required {field}", field)

    if op.payload_builder:
        return op.payload_builder(**kwargs)
    return {}
```

**Impact**:
- Complexity per server: E (31-35) → C (15-20) or better
- Lines per server: 230 → 150 (35% reduction)
- Easier to test: Each operation definition is independently testable

---

### 3. Simplify main() Function Structure

**Current pattern** (high complexity):
```python
def main(operation, path, content, ..., dry_run, timeout, client, context):
    # 1. Operation validation (5-10 lines)
    # 2. Credential validation (5-10 lines)
    # 3. Build payload via if-elif chain (50-100 lines)
    # 4. Dry run check (10-15 lines)
    # 5. Build URL (10-20 lines)
    # 6. Execute request (10-20 lines)
    # 7. Handle response (20-30 lines)
```

**Proposed pattern** (low complexity):
```python
def main(operation, path, content, ..., dry_run, timeout, client, context):
    # 1. Validate operation
    if operation not in _OPERATIONS:
        return validation_error("Unsupported operation", field="operation")

    # 2. Validate credentials
    if not API_TOKEN:
        return error_output("Missing API_TOKEN", status_code=401)

    # 3. Build payload (delegates to dispatch table)
    result = _validate_and_build_payload(operation, path=path, content=content, ...)
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])
    payload = result

    # 4. Build URL
    url = f"{_BASE_URL}/{_ENDPOINT_MAP[operation]}"

    # 5. Dry run
    if dry_run:
        return {"output": {"preview": {"url": url, "payload": payload}}}

    # 6. Execute and return
    return _execute_request(url, payload, headers, timeout, client)
```

**Impact**: main() complexity drops from 30+ to ~12.

---

### 4. Extract Request Execution to Shared Helper

**Problem**: Every server has nearly identical request execution code:

```python
try:
    response = api_client.post(url, headers=headers, json=payload, timeout=timeout)
except requests.RequestException as exc:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return error_output("Request failed", status_code=status, details=str(exc))

try:
    data = response.json()
except ValueError:
    return error_output("Invalid JSON", status_code=response.status_code, details=response.text)

if not response.ok:
    return error_output(data.get("error", "API error"), status_code=response.status_code)

return {"output": data}
```

**Solution**: Extract to `server_utils.external_api`:

```python
# In server_utils/external_api/executor.py
def execute_json_request(
    client: ExternalApiClient,
    method: str,
    url: str,
    *,
    headers: dict = None,
    json: dict = None,
    timeout: int = 60,
    error_key: str = "error",
) -> dict:
    """Execute request and return standardized response."""
    try:
        response = getattr(client, method.lower())(url, headers=headers, json=json, timeout=timeout)
    except requests.RequestException as exc:
        return error_output("Request failed", status_code=_get_status(exc), details=str(exc))

    try:
        data = response.json()
    except ValueError:
        return error_output("Invalid JSON", status_code=response.status_code, details=response.text)

    if not response.ok:
        return error_output(data.get(error_key, "API error"), status_code=response.status_code)

    return {"output": data}
```

**Impact**: Removes 20-25 lines from every server definition.

---

### 5. Remove Backward Compatibility Cruft

The current servers include unnecessary defensive code:

```python
# Unnecessary - just use the value directly
normalized_operation = operation.lower()  # Just require lowercase input

# Unnecessary - empty string is already falsy
if not path:
    path = ""  # Redundant

# Unnecessary - getattr chain
status = getattr(getattr(exc, "response", None), "status_code", None)  # Just use try/except
```

**Solution**: Simplify and break backward compatibility where it adds complexity.

---

## Pylint Configuration for Structural Issues

Add these Pylint checks to catch structural problems early:

```ini
# In .pylintrc or pyproject.toml

[DESIGN]
# Maximum branches in a function (if/elif/else)
max-branches = 12

# Maximum statements in a function
max-statements = 50

# Maximum local variables in a function
max-locals = 15

# Maximum arguments for a function
max-args = 8

# Maximum nesting level
max-nested-blocks = 4

[MASTER]
# Enable McCabe complexity checker
load-plugins = pylint.extensions.mccabe

[MCCABE]
# Maximum cyclomatic complexity
max-complexity = 15
```

**New checks this would catch**:

| Check | Current Violations | Benefit |
|-------|-------------------|---------|
| max-branches | 25+ servers (10-15 branches each) | Forces dispatch table pattern |
| max-statements | Most servers (80-120 statements) | Forces function extraction |
| max-complexity | 25 servers (31-35 complexity) | Direct complexity gate |
| max-locals | Many servers (15-25 locals) | Forces data objects |

---

## Implementation Priority

### Phase 1: Quick Wins (Days)
1. Extract duplicate endpoint maps to module constants
2. Add Pylint configuration for structural checks
3. Run Pylint to identify worst offenders

### Phase 2: Dispatch Tables (Weeks)
1. Create `Operation` dataclass in server_utils
2. Migrate highest-complexity servers first (dropbox, telegram, salesforce)
3. Validate with existing tests

### Phase 3: Shared Execution (Weeks)
1. Create `execute_json_request` helper
2. Update servers to use it
3. Remove duplicated error handling code

---

## Expected Outcomes

| Metric | Current | Target |
|--------|---------|--------|
| Average server complexity | E (31-35) | C (11-15) |
| Lines per server | 200-250 | 100-130 |
| Duplicate code | ~40% | <10% |
| Time to add new operation | 30+ lines | 3-5 lines |

---

## Breaking Changes (Acceptable)

1. **Operation names must be lowercase** - Remove `.lower()` normalization
2. **Empty strings are not converted** - Require explicit empty string or None
3. **Error message format changes** - Standardize on common format

These breaking changes simplify the codebase significantly. Since this is internal API code, the migration cost is low.
