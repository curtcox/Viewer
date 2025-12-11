# AI Assist Server Implementation Plan with Evaluation Suite

## Overview

This document provides a detailed plan for implementing an `ai_assist` server that uses real AI (via OpenRouter API) to replace the current `ai_stub` server in the default boot template. The plan includes comprehensive use cases for every AI button location in the application, along with automated tests to verify functionality.

## Implementation Plan

### 1. Server Implementation (`ai_assist`)

**Location:** `reference_templates/servers/definitions/ai_assist.py`

**Requirements:**
- ✅ Same REST API interface as `ai_stub` (maintains backward compatibility)
- ✅ Implemented using auto-main server pattern
- ✅ Uses OpenRouter API for actual AI completion
- ✅ Configurable model and provider via variables

**API Specification:**

**Endpoint:** `/ai_assist` (with alias `/ai`)

**Request Format (POST):**
```json
{
  "request_text": "Add error handling for invalid input",
  "original_text": "def process(data):\n    return data.strip()",
  "target_label": "server definition",
  "context_data": {"form": "server_form", "server_name": "my_server"},
  "form_summary": {"definition": "def process(data):\n    return data.strip()"}
}
```

**Response Format:**
```json
{
  "updated_text": "def process(data):\n    if not data:\n        raise ValueError('Data cannot be empty')\n    return data.strip()",
  "message": "Added error handling for invalid input",
  "context_summary": "Applied to: server definition\nContext: server_form"
}
```

**Implementation Outline:**

```python
def main(
    request_text: str,
    original_text: str = "",
    target_label: str = "content",
    context_data: dict = None,
    form_summary: dict = None,
    *,
    OPENROUTER_API_KEY: str,
    AI_MODEL: str = None,
    AI_PROVIDER: str = None,
    context=None
):
    """
    AI-powered text transformation using OpenRouter API.

    Parameters auto-resolved from:
    - JSON request body (request_text, original_text, etc.)
    - Variables: AI_MODEL, AI_PROVIDER (default from env)
    - Secrets: OPENROUTER_API_KEY (required)
    """

    # 1. Determine model (priority: variable > env > default)
    model = AI_MODEL or os.getenv("AI_MODEL") or "anthropic/claude-sonnet-4-20250514"

    # 2. Build context-aware prompt
    prompt = build_ai_prompt(
        request_text=request_text,
        original_text=original_text,
        target_label=target_label,
        context_data=context_data or {},
        form_summary=form_summary or {}
    )

    # 3. Call OpenRouter API
    response = call_openrouter(
        api_key=OPENROUTER_API_KEY,
        model=model,
        prompt=prompt
    )

    # 4. Parse and format response
    updated_text = extract_updated_text(response)

    # 5. Return in ai_stub-compatible format
    return {
        "updated_text": updated_text,
        "message": f"Applied: {request_text}",
        "context_summary": format_context_summary(context_data, form_summary),
        "model_used": model,
        "provider": AI_PROVIDER or "openrouter"
    }
```

**Key Implementation Details:**

1. **Prompt Engineering:**
   - System prompt: "You are a helpful AI assistant for a web application. Users will ask you to modify text content. Return ONLY the modified content without explanations."
   - User prompt includes: original text, requested change, context about what's being edited
   - Use structured format to guide AI output

2. **Error Handling:**
   - Graceful fallback if API fails (return original text with error message)
   - Timeout handling (30s default)
   - API key validation
   - Rate limiting awareness

3. **Configuration Variables:**
   - `AI_MODEL`: Model identifier (e.g., "anthropic/claude-sonnet-4-20250514", "openai/gpt-4", "google/gemini-pro")
   - `AI_PROVIDER`: Provider name for logging/debugging (defaults to "openrouter")
   - `AI_MAX_TOKENS`: Max tokens in response (default: 4096)
   - `AI_TEMPERATURE`: Creativity level (default: 0.3 for consistent edits)

4. **Secret Management:**
   - `OPENROUTER_API_KEY`: Required secret, validated at runtime
   - Clear error message if missing

### 2. Server Template

**Location:** `reference_templates/servers/templates/ai_assist.json`

```json
{
  "id": "ai-assist",
  "name": "AI Assist",
  "description": "AI-powered text transformation using OpenRouter API. Supports multiple models and providers via configuration variables.",
  "definition_file": "reference_templates/servers/definitions/ai_assist.py",
  "category": "ai",
  "tags": ["ai", "text-transformation", "openrouter"],
  "required_secrets": ["OPENROUTER_API_KEY"],
  "optional_variables": ["AI_MODEL", "AI_PROVIDER", "AI_MAX_TOKENS", "AI_TEMPERATURE"],
  "default_variables": {
    "AI_MODEL": "anthropic/claude-sonnet-4-20250514",
    "AI_TEMPERATURE": "0.3",
    "AI_MAX_TOKENS": "4096"
  }
}
```

### 3. Boot Template Integration

**Update:** `reference_templates/boot.source.json`

```json
{
  "servers": [
    {
      "name": "ai_assist",
      "definition_cid": "reference_templates/servers/definitions/ai_assist.py",
      "enabled": true
    }
  ],
  "aliases": [
    {
      "name": "ai",
      "definition_cid": "reference_templates/aliases/ai_assist.txt",
      "enabled": true
    }
  ],
  "variables": [
    {
      "name": "AI_MODEL",
      "value": "anthropic/claude-sonnet-4-20250514",
      "description": "AI model to use for text transformations"
    },
    {
      "name": "AI_TEMPERATURE",
      "value": "0.3",
      "description": "AI temperature (0.0-1.0, lower = more consistent)"
    },
    {
      "name": "AI_MAX_TOKENS",
      "value": "4096",
      "description": "Maximum tokens in AI response"
    }
  ]
}
```

**Update Alias:** `reference_templates/aliases/ai_assist.txt`
```
/ai_assist
```

### 4. Default Resource Setup

**Update:** `identity.py` - `ensure_default_resources()`

Add function to initialize ai_assist server if not present:

```python
def ensure_ai_assist():
    """Ensure AI assist server exists in boot template."""
    # Check if ai_assist server exists
    # If not, add from reference template
    # Set up default variables
    # Ensure OPENROUTER_API_KEY secret is documented
```

## AI Button Use Cases

This section documents all 8 locations where AI buttons appear in the application, with realistic use cases for each.

### Use Case 1: Server Definition Editor

**Location:** Server Form (`/server/edit?name=hello_world`)

**Page URL:** `http://localhost:5000/server/edit?name=hello_world`

**Context:** User is editing a server definition and wants to add functionality.

**Initial Content:**
```python
def main(name="World"):
    """Simple greeting server."""
    return {
        "output": f"Hello, {name}!",
        "content_type": "text/plain"
    }
```

**User Request:** "Add input validation to reject empty names"

**Expected AI Output:**
```python
def main(name="World"):
    """Simple greeting server."""
    if not name or not name.strip():
        return {
            "output": "Error: Name cannot be empty",
            "content_type": "text/plain",
            "status": 400
        }
    return {
        "output": f"Hello, {name}!",
        "content_type": "text/plain"
    }
```

**Verification:**
- Code contains empty name check
- Returns 400 status for invalid input
- Preserves original functionality for valid input

---

### Use Case 2: Server Definition - Add Logging

**Location:** Server Form (`/server/edit?name=data_processor`)

**Page URL:** `http://localhost:5000/server/edit?name=data_processor`

**Initial Content:**
```python
def main(data=""):
    """Process incoming data."""
    processed = data.upper()
    return {
        "output": processed,
        "content_type": "text/plain"
    }
```

**User Request:** "Add logging before and after processing"

**Expected AI Output:**
```python
import logging

def main(data=""):
    """Process incoming data."""
    logging.info(f"Processing data: {data[:50]}...")
    processed = data.upper()
    logging.info(f"Processed result: {processed[:50]}...")
    return {
        "output": processed,
        "content_type": "text/plain"
    }
```

**Verification:**
- Import logging added
- Two logging statements present
- Original functionality preserved

---

### Use Case 3: Alias Definition

**Location:** Alias Form (`/alias/edit?name=hello`)

**Page URL:** `http://localhost:5000/alias/edit?name=hello`

**Context:** User is creating a URL alias for a server.

**Initial Content:**
```
/servers/hello_world
```

**User Request:** "Add query parameters for name and greeting style"

**Expected AI Output:**
```
/servers/hello_world?name=Friend&style=formal
```

**Verification:**
- Original path preserved
- Query parameters added
- Valid URL format

---

### Use Case 4: CID Content Editor

**Location:** CID Editor (`/cid/edit?id=abc123def456`)

**Page URL:** `http://localhost:5000/cid/edit?id=abc123def456`

**Context:** User is editing content-addressable storage content.

**Initial Content:**
```json
{
  "users": [
    {"name": "Alice", "role": "admin"},
    {"name": "Bob", "role": "user"}
  ]
}
```

**User Request:** "Add an email field to each user"

**Expected AI Output:**
```json
{
  "users": [
    {"name": "Alice", "role": "admin", "email": "alice@example.com"},
    {"name": "Bob", "role": "user", "email": "bob@example.com"}
  ]
}
```

**Verification:**
- Valid JSON structure maintained
- Email field added to all users
- Original fields preserved

---

### Use Case 5: Upload Form - Text Content

**Location:** Upload Form (`/upload`)

**Page URL:** `http://localhost:5000/upload`

**Context:** User is uploading text content and wants AI assistance to format it.

**Initial Content:**
```
Product Features
Fast Performance
Easy to Use
Secure
```

**User Request:** "Convert to markdown list with descriptions"

**Expected AI Output:**
```markdown
# Product Features

- **Fast Performance**: Optimized for speed and efficiency
- **Easy to Use**: Intuitive interface requires no training
- **Secure**: Enterprise-grade security built-in
```

**Verification:**
- Markdown format applied
- Original items preserved
- Descriptions added appropriately

---

### Use Case 6: Import Form - Data Transformation

**Location:** Import Form (`/import`)

**Page URL:** `http://localhost:5000/import`

**Context:** User is importing data from another system.

**Initial Content:**
```csv
Name,Status,Priority
Task 1,open,high
Task 2,closed,low
Task 3,open,medium
```

**User Request:** "Convert to JSON array of objects"

**Expected AI Output:**
```json
[
  {"name": "Task 1", "status": "open", "priority": "high"},
  {"name": "Task 2", "status": "closed", "priority": "low"},
  {"name": "Task 3", "status": "open", "priority": "medium"}
]
```

**Verification:**
- Valid JSON structure
- All data converted correctly
- Field names lowercase

---

### Use Case 7: Secret Definition

**Location:** Secret Form (`/secret/edit?name=API_CONFIG`)

**Page URL:** `http://localhost:5000/secret/edit?name=API_CONFIG`

**Context:** User is defining a secret value for API configuration.

**Initial Content:**
```json
{
  "endpoint": "https://api.example.com",
  "timeout": 30
}
```

**User Request:** "Add retry configuration with 3 attempts and exponential backoff"

**Expected AI Output:**
```json
{
  "endpoint": "https://api.example.com",
  "timeout": 30,
  "retry": {
    "max_attempts": 3,
    "backoff_strategy": "exponential",
    "initial_delay_ms": 1000
  }
}
```

**Verification:**
- Valid JSON structure
- Retry configuration added
- Original fields preserved

---

### Use Case 8: Variable Definition

**Location:** Variable Form (`/variable/edit?name=APP_CONFIG`)

**Page URL:** `http://localhost:5000/variable/edit?name=APP_CONFIG`

**Context:** User is defining application configuration.

**Initial Content:**
```json
{
  "app_name": "Viewer",
  "version": "1.0.0"
}
```

**User Request:** "Add feature flags for dark mode and experimental features"

**Expected AI Output:**
```json
{
  "app_name": "Viewer",
  "version": "1.0.0",
  "features": {
    "dark_mode": true,
    "experimental_features": false
  }
}
```

**Verification:**
- Valid JSON structure
- Feature flags added with boolean values
- Original configuration preserved

---

### Use Case 9: Server Test Card - Query Parameters

**Location:** Server Test Card (`/server/test?name=api_endpoint`)

**Page URL:** `http://localhost:5000/server/test?name=api_endpoint`

**Context:** User is testing a server and wants to add query parameters.

**Initial Content:**
```
page=1&limit=10
```

**User Request:** "Add filtering by status and sorting by date descending"

**Expected AI Output:**
```
page=1&limit=10&status=active&sort=date&order=desc
```

**Verification:**
- Original parameters preserved
- New parameters added with appropriate values
- Valid query string format

## Test Specifications

### Test Strategy Overview

**Approach:** Flask Test Client (NOT Selenium WebDriver)

These tests verify AI functionality by making direct HTTP requests using Flask's test client. Each test is essentially a single POST request with setup and validation - perfect for the test client approach.

**Why Test Client instead of Browser Automation:**
1. **Simplicity**: AI interactions are single POST requests with JSON payloads
2. **Speed**: 10-20x faster than Selenium (no browser startup overhead)
3. **Reliability**: No browser flakiness, timing issues, or WebDriver management
4. **Existing Pattern**: Follows `test_ai_stub_server.py` and `test_ai_editor_integration.py`
5. **Minimal Dependencies**: Just pytest + Flask (no ChromeDriver, Selenium, etc.)

**Note on One-Shot Runs:**
The codebase has a "one-shot runs" feature for making requests without a full web server, but it currently only supports GET requests. Since AI interactions require POST with JSON payloads, we use Flask test client. See "Future Enhancements" for potential extension of one-shot runs to support POST/PUT/DELETE.

### Test Organization

**Location:** `tests/ai_use_cases/`

This is a NEW test directory specifically for AI evaluation tests, separate from existing integration tests.

```
tests/ai_use_cases/
├── __init__.py
├── conftest.py                           # Fixtures for AI testing
├── test_server_definition_editor.py      # Use cases 1-2
├── test_alias_editor.py                  # Use case 3
├── test_cid_editor.py                    # Use case 4
├── test_upload_form.py                   # Use case 5
├── test_import_form.py                   # Use case 6
├── test_secret_form.py                   # Use case 7
├── test_variable_form.py                 # Use case 8
└── test_server_test_card.py              # Use case 9
```

### Test Framework

**Technology:** Pytest + Flask Test Client (using existing test infrastructure)

**Why Flask Test Client instead of Selenium:**
- AI interactions are single POST requests with JSON payloads - perfect for test client
- No browser automation needed - tests are faster and more reliable
- Follows the pattern from existing AI tests (`test_ai_stub_server.py`)
- Simpler setup with no ChromeDriver or Selenium dependencies
- Can use the existing `memory_client` fixture from `tests/conftest.py`

**Note on One-Shot Runs:**
The codebase has a "one-shot runs" feature (`cli.py:make_http_get_request()`) that allows making requests without a full web server, but it currently only supports GET requests. Since AI interactions require POST with JSON payloads, we use Flask test client. A future enhancement could extend one-shot runs to support POST/PUT/DELETE operations.

**Fixtures Required:** (`conftest.py`)
```python
import pytest
import os
import json

@pytest.fixture(scope="session")
def requires_openrouter_api_key():
    """Skip tests if OPENROUTER_API_KEY not available."""
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set - skipping AI evaluation tests")

@pytest.fixture(autouse=True)
def setup_ai_assist_server(memory_db_app):
    """Ensure ai_assist server is enabled and configured."""
    with memory_db_app.app_context():
        from database import db
        from models import Server, Variable, Secret

        # Create ai_assist server if not exists
        ai_server = db.session.query(Server).filter_by(name='ai_assist').first()
        if not ai_server:
            with open('reference_templates/servers/definitions/ai_assist.py') as f:
                definition = f.read()

            ai_server = Server(
                name='ai_assist',
                definition=definition,
                enabled=True
            )
            db.session.add(ai_server)

        # Ensure OPENROUTER_API_KEY secret exists
        api_key = os.getenv('OPENROUTER_API_KEY')
        if api_key:
            secret = db.session.query(Secret).filter_by(name='OPENROUTER_API_KEY').first()
            if not secret:
                secret = Secret(name='OPENROUTER_API_KEY', value=api_key)
                db.session.add(secret)

        # Set default AI model variable
        ai_model = db.session.query(Variable).filter_by(name='AI_MODEL').first()
        if not ai_model:
            ai_model = Variable(
                name='AI_MODEL',
                value=os.getenv('AI_MODEL', 'anthropic/claude-sonnet-4-20250514')
            )
            db.session.add(ai_model)

        db.session.commit()

    yield

@pytest.fixture
def ai_interaction_tracker():
    """Track AI interactions for debugging and analysis."""
    interactions = []

    def record(request_payload, response_data, status_code):
        interactions.append({
            'request': request_payload,
            'response': response_data,
            'status': status_code,
            'timestamp': datetime.utcnow()
        })

    yield record

    # Save interactions if test fails (pytest_runtest_makereport hook)
```

### Test Template

Each test follows this pattern (adapted from `tests/test_ai_stub_server.py`):

```python
def test_use_case_name(memory_client, requires_openrouter_api_key, ai_interaction_tracker):
    """
    Test Case: [Description]

    Given: [Initial state]
    When: [User submits AI request]
    Then: [Expected AI transformation applied]
    """
    # 1. Prepare test data
    INITIAL_CONTENT = """
    def main(name="World"):
        return {"output": f"Hello, {name}!"}
    """

    USER_REQUEST = "Add input validation to reject empty names"

    # 2. Build AI request payload (matches ai_stub/ai_assist API)
    payload = {
        'request_text': USER_REQUEST,
        'original_text': INITIAL_CONTENT,
        'target_label': 'server definition',
        'context_data': {
            'form': 'server_form',
            'server_name': 'hello_world'
        },
        'form_summary': {
            'definition': INITIAL_CONTENT
        }
    }

    # 3. Make POST request to /ai endpoint
    response = memory_client.post(
        '/ai',
        json=payload,
        follow_redirects=True
    )

    # 4. Track interaction for debugging
    ai_interaction_tracker(payload, response.get_json(), response.status_code)

    # 5. Verify response status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.content_type == 'application/json'

    # 6. Parse response data
    data = response.get_json()
    assert 'updated_text' in data, "Response missing 'updated_text' field"

    updated_text = data['updated_text']

    # 7. Verify AI transformation
    assert_ai_output_valid(updated_text)
    assert_original_content_preserved(updated_text, INITIAL_CONTENT)
    assert_requested_change_applied(updated_text, USER_REQUEST)

    # 8. Verify specific expectations for this use case
    assert 'if not name' in updated_text, "Missing input validation check"
    assert_valid_python(updated_text)
```

**Key Differences from Selenium Approach:**
- **No browser needed**: Direct HTTP client calls (faster, more reliable)
- **No WebDriver waits**: Synchronous request/response (simpler)
- **No element selectors**: JSON payloads and responses (cleaner)
- **Follows existing patterns**: Consistent with `test_ai_stub_server.py` and `test_ai_editor_integration.py`
- **Single function call**: Each test is essentially one POST request with setup and validation

### Individual Test Specifications

#### Test 1: Server Definition - Input Validation

**File:** `tests/ai_use_cases/test_server_definition_editor.py::test_add_input_validation`

**Test Implementation:**
```python
def test_add_input_validation(memory_client, requires_openrouter_api_key, ai_interaction_tracker):
    """Test AI adds input validation to server definition."""
    # Use Case 1 initial content
    original_text = 'def main(name="World"):\n    """Simple greeting server."""\n    return {\n        "output": f"Hello, {name}!",\n        "content_type": "text/plain"\n    }'

    payload = {
        'request_text': 'Add input validation to reject empty names',
        'original_text': original_text,
        'target_label': 'server definition',
        'context_data': {'form': 'server_form', 'server_name': 'hello_world'},
        'form_summary': {'definition': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    ai_interaction_tracker(payload, response.get_json(), response.status_code)

    assert response.status_code == 200
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify input validation added
    assert 'if not name' in updated_text or 'if name' in updated_text
    assert 'strip()' in updated_text or 'empty' in updated_text.lower()

    # Verify error handling
    assert '400' in updated_text or 'error' in updated_text.lower()

    # Verify original logic preserved
    assert 'Hello' in updated_text
    assert 'name' in updated_text

    # Verify valid Python
    assert_valid_python(updated_text)

    # Verify function signature preserved
    assert 'def main(' in updated_text
```

---

#### Test 2: Server Definition - Add Logging

**File:** `tests/ai_use_cases/test_server_definition_editor.py::test_add_logging`

**Test Implementation:**
```python
def test_add_logging(memory_client, requires_openrouter_api_key):
    """Test AI adds logging to server definition."""
    original_text = 'def main(data=""):\n    """Process incoming data."""\n    processed = data.upper()\n    return {\n        "output": processed,\n        "content_type": "text/plain"\n    }'

    payload = {
        'request_text': 'Add logging before and after processing',
        'original_text': original_text,
        'target_label': 'server definition',
        'context_data': {'form': 'server_form'},
        'form_summary': {'definition': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify logging import added
    assert 'import logging' in updated_text

    # Verify logging calls present
    logging_calls = updated_text.count('logging.info') + updated_text.count('logging.debug')
    assert logging_calls >= 2, f"Expected at least 2 logging calls, found {logging_calls}"

    # Verify original logic preserved
    assert '.upper()' in updated_text
    assert 'processed' in updated_text

    assert_valid_python(updated_text)
```

---

#### Test 3: Alias Definition - Add Query Parameters

**File:** `tests/ai_use_cases/test_alias_editor.py::test_add_query_parameters`

**Test Implementation:**
```python
def test_add_query_parameters(memory_client, requires_openrouter_api_key):
    """Test AI adds query parameters to alias."""
    original_text = '/servers/hello_world'

    payload = {
        'request_text': 'Add query parameters for name and greeting style',
        'original_text': original_text,
        'target_label': 'alias definition',
        'context_data': {'form': 'alias_form'},
        'form_summary': {'definition': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify original path preserved
    assert '/servers/hello_world' in updated_text

    # Verify query parameters added
    assert '?' in updated_text
    assert 'name=' in updated_text
    assert 'style=' in updated_text or 'greeting=' in updated_text

    # Verify reasonable length
    assert len(updated_text) < 500
```

---

#### Test 4: CID Editor - Add JSON Fields

**File:** `tests/ai_use_cases/test_cid_editor.py::test_add_email_field`

**Test Implementation:**
```python
def test_add_email_field(memory_client, requires_openrouter_api_key):
    """Test AI adds email field to JSON objects."""
    original_text = '''{"users": [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "user"}
    ]}'''

    payload = {
        'request_text': 'Add an email field to each user',
        'original_text': original_text,
        'target_label': 'CID content',
        'context_data': {'form': 'cid_editor'},
        'form_summary': {'content': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify valid JSON
    parsed = assert_valid_json(updated_text)

    # Verify all users have email field
    assert 'users' in parsed
    assert len(parsed['users']) == 2
    for user in parsed['users']:
        assert 'email' in user, f"User {user['name']} missing email"
        assert '@' in user['email']

    # Verify original fields preserved
    assert parsed['users'][0]['name'] == 'Alice'
    assert parsed['users'][0]['role'] == 'admin'
```

---

#### Test 5: Upload Form - Markdown Conversion

**File:** `tests/ai_use_cases/test_upload_form.py::test_convert_to_markdown_list`

**Test Implementation:**
```python
def test_convert_to_markdown_list(memory_client, requires_openrouter_api_key):
    """Test AI converts plain text to markdown list."""
    original_text = '''Product Features
Fast Performance
Easy to Use
Secure'''

    payload = {
        'request_text': 'Convert to markdown list with descriptions',
        'original_text': original_text,
        'target_label': 'text content',
        'context_data': {'form': 'upload'},
        'form_summary': {'text_content': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify markdown list markers
    assert '-' in updated_text or '*' in updated_text or '1.' in updated_text

    # Verify bold markers for emphasis
    assert '**' in updated_text

    # Verify original items present
    assert 'Fast Performance' in updated_text or 'fast performance' in updated_text.lower()
    assert 'Easy to Use' in updated_text or 'easy to use' in updated_text.lower()
    assert 'Secure' in updated_text or 'secure' in updated_text.lower()

    # Verify descriptions added
    assert len(updated_text) > len(original_text) * 1.5
```

---

#### Test 6: Import Form - CSV to JSON

**File:** `tests/ai_use_cases/test_import_form.py::test_csv_to_json_conversion`

**Test Implementation:**
```python
def test_csv_to_json_conversion(memory_client, requires_openrouter_api_key):
    """Test AI converts CSV to JSON array."""
    original_text = '''Name,Status,Priority
Task 1,open,high
Task 2,closed,low
Task 3,open,medium'''

    payload = {
        'request_text': 'Convert to JSON array of objects',
        'original_text': original_text,
        'target_label': 'import data',
        'context_data': {'form': 'import'},
        'form_summary': {'import_text': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify valid JSON
    parsed = assert_valid_json(updated_text)

    # Verify array structure
    assert isinstance(parsed, list), "Expected JSON array"
    assert len(parsed) == 3, f"Expected 3 items, got {len(parsed)}"

    # Verify all fields present
    for item in parsed:
        assert 'name' in item or 'Name' in item
        assert 'status' in item or 'Status' in item
        assert 'priority' in item or 'Priority' in item

    # Verify data values preserved
    task_names = [item.get('name', item.get('Name')) for item in parsed]
    assert any('Task 1' in name for name in task_names)
```

---

#### Test 7: Secret Form - Add Retry Config

**File:** `tests/ai_use_cases/test_secret_form.py::test_add_retry_configuration`

**Test Implementation:**
```python
def test_add_retry_configuration(memory_client, requires_openrouter_api_key):
    """Test AI adds retry configuration to JSON."""
    original_text = '''{
    "endpoint": "https://api.example.com",
    "timeout": 30
}'''

    payload = {
        'request_text': 'Add retry configuration with 3 attempts and exponential backoff',
        'original_text': original_text,
        'target_label': 'secret value',
        'context_data': {'form': 'secret_form'},
        'form_summary': {'value': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify valid JSON
    parsed = assert_valid_json(updated_text)

    # Verify original fields preserved
    assert parsed['endpoint'] == 'https://api.example.com'
    assert parsed['timeout'] == 30

    # Verify retry configuration added
    assert 'retry' in parsed
    retry = parsed['retry']
    assert retry.get('max_attempts') == 3 or retry.get('attempts') == 3
    assert 'exponential' in str(retry.get('backoff_strategy', '')).lower() or \
           'exponential' in str(retry.get('backoff', '')).lower()
```

---

#### Test 8: Variable Form - Add Feature Flags

**File:** `tests/ai_use_cases/test_variable_form.py::test_add_feature_flags`

**Test Implementation:**
```python
def test_add_feature_flags(memory_client, requires_openrouter_api_key):
    """Test AI adds feature flags to configuration JSON."""
    original_text = '''{
    "app_name": "Viewer",
    "version": "1.0.0"
}'''

    payload = {
        'request_text': 'Add feature flags for dark mode and experimental features',
        'original_text': original_text,
        'target_label': 'variable value',
        'context_data': {'form': 'variable_form'},
        'form_summary': {'value': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify valid JSON
    parsed = assert_valid_json(updated_text)

    # Verify original fields preserved
    assert parsed['app_name'] == 'Viewer'
    assert parsed['version'] == '1.0.0'

    # Verify features object added
    assert 'features' in parsed
    features = parsed['features']

    # Verify dark mode flag
    assert 'dark_mode' in features or 'darkMode' in features
    dark_mode_value = features.get('dark_mode', features.get('darkMode'))
    assert isinstance(dark_mode_value, bool)

    # Verify experimental features flag
    assert 'experimental_features' in features or 'experimental' in features
```

---

#### Test 9: Server Test Card - Add Query Filters

**File:** `tests/ai_use_cases/test_server_test_card.py::test_add_query_filters`

**Test Implementation:**
```python
def test_add_query_filters(memory_client, requires_openrouter_api_key):
    """Test AI adds query parameters for filtering and sorting."""
    original_text = 'page=1&limit=10'

    payload = {
        'request_text': 'Add filtering by status and sorting by date descending',
        'original_text': original_text,
        'target_label': 'query parameters',
        'context_data': {'form': 'server_test'},
        'form_summary': {'query_params': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    data = response.get_json()
    updated_text = data['updated_text']

    # Verify original params preserved
    assert 'page=1' in updated_text
    assert 'limit=10' in updated_text

    # Verify status filter added
    assert 'status=' in updated_text

    # Verify sort/order parameters added
    assert 'sort=' in updated_text or 'order=' in updated_text or 'orderBy=' in updated_text

    # Verify valid query string format
    assert_valid_query_string(updated_text)
```

---

### Test Utilities

**File:** `tests/ai_use_cases/assertions.py`

```python
"""Common assertion helpers for AI use case tests."""

import json
import ast
from urllib.parse import parse_qs

def assert_ai_output_valid(output: str):
    """Verify AI output is not empty and contains no error markers."""
    assert output, "AI output is empty"
    assert len(output) > 10, "AI output too short"
    assert "error" not in output.lower()[:100], "AI response contains error"

def assert_valid_python(code: str):
    """Verify string is valid Python code."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Invalid Python syntax: {e}")

def assert_valid_json(text: str) -> dict:
    """Verify and parse JSON."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON: {e}")

def assert_original_content_preserved(result: str, original: str):
    """Verify key elements from original content are in result."""
    # Extract key identifiers from original
    # Verify they appear in result
    pass

def assert_requested_change_applied(result: str, request: str):
    """Verify the requested change is reflected in result."""
    # Parse request for key terms
    # Verify result contains evidence of change
    pass

def assert_valid_query_string(qs: str):
    """Verify valid query string format."""
    assert "?" not in qs or qs.count("?") == 1, "Invalid query string"
    # Parse and validate
    parsed = parse_qs(qs.split("?")[-1])
    assert len(parsed) > 0, "No query parameters found"
```

## Test Execution

### Local Execution

**Script:** `run_ai_eval_tests.sh`

```bash
#!/bin/bash
# Run AI evaluation tests locally using Flask test client
# No web server or browser needed - tests use memory database

set -e

echo "AI Evaluation Tests (Flask Test Client)"
echo "========================================"

# 1. Check for OpenRouter API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY environment variable not set"
    echo "Set it with: export OPENROUTER_API_KEY=your_key_here"
    exit 1
fi

# 2. Set AI model (optional)
export AI_MODEL="${AI_MODEL:-anthropic/claude-sonnet-4-20250514}"
echo "Using AI model: $AI_MODEL"

# 3. Run tests with coverage
# Note: No need to start web server - tests use memory_client fixture
echo ""
echo "Running AI evaluation tests..."
pytest tests/ai_use_cases/ \
    --verbose \
    --tb=short \
    --junit-xml=test-results/ai-eval-results.xml \
    --html=test-results/ai-eval-report.html \
    --self-contained-html \
    --cov=reference_templates.servers.definitions.ai_assist \
    --cov-report=html:test-results/ai-eval-coverage \
    --cov-report=term-missing

echo ""
echo "========================================"
echo "Test Results:"
echo "  - JUnit XML: test-results/ai-eval-results.xml"
echo "  - HTML Report: test-results/ai-eval-report.html"
echo "  - Coverage: test-results/ai-eval-coverage/index.html"
echo "========================================"
```

**Usage:**
```bash
# Set API key
export OPENROUTER_API_KEY=sk-or-v1-...

# Run all AI evaluation tests
./run_ai_eval_tests.sh

# Run specific test file
pytest tests/ai_use_cases/test_server_definition_editor.py -v

# Run specific test case
pytest tests/ai_use_cases/test_server_definition_editor.py::test_add_input_validation -v

# Run with different model
AI_MODEL=openai/gpt-4 ./run_ai_eval_tests.sh

# Run with specific OpenRouter model
AI_MODEL=google/gemini-pro-1.5 OPENROUTER_API_KEY=your_key ./run_ai_eval_tests.sh
```

**Benefits of Test Client Approach:**
- **Fast**: No browser startup overhead (typically 10-20x faster than Selenium)
- **Simple**: No ChromeDriver installation or management
- **Reliable**: No browser flakiness or timing issues
- **Lightweight**: Minimal dependencies (just pytest and Flask test client)
- **Debuggable**: Direct Python debugging, no browser automation complexity

### CI Execution - On-Demand Workflow

**File:** `.github/workflows/ai-evaluation.yml`

```yaml
name: AI Evaluation Tests

on:
  workflow_dispatch:
    inputs:
      ai_model:
        description: 'AI Model to use for testing'
        required: false
        default: 'anthropic/claude-sonnet-4-20250514'
        type: choice
        options:
          - anthropic/claude-sonnet-4-20250514
          - anthropic/claude-3-5-sonnet-20241022
          - openai/gpt-4-turbo
          - openai/gpt-4
          - google/gemini-pro-1.5
      test_pattern:
        description: 'Test pattern to run (e.g., test_server_* or leave empty for all)'
        required: false
        default: ''

jobs:
  ai-evaluation:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-html pytest-cov

      - name: Run AI evaluation tests
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          AI_MODEL: ${{ github.event.inputs.ai_model }}
        run: |
          # Tests use Flask test client - no web server or browser needed
          TEST_PATTERN="${{ github.event.inputs.test_pattern }}"
          if [ -z "$TEST_PATTERN" ]; then
            pytest tests/ai_use_cases/ \
              --verbose \
              --junit-xml=test-results/ai-eval-results.xml \
              --html=test-results/ai-eval-report.html \
              --self-contained-html \
              --cov=reference_templates.servers.definitions.ai_assist \
              --cov-report=html:test-results/ai-eval-coverage \
              --cov-report=xml:test-results/coverage.xml
          else
            pytest "tests/ai_use_cases/${TEST_PATTERN}.py" \
              --verbose \
              --junit-xml=test-results/ai-eval-results.xml \
              --html=test-results/ai-eval-report.html \
              --self-contained-html
          fi

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ai-evaluation-results
          path: test-results/
          retention-days: 30

      - name: Generate test summary
        if: always()
        run: |
          python scripts/generate_ai_eval_summary.py \
            test-results/ai-eval-results.xml > $GITHUB_STEP_SUMMARY

  publish-results:
    needs: ai-evaluation
    if: always()
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download test results
        uses: actions/download-artifact@v4
        with:
          name: ai-evaluation-results
          path: test-results/

      - name: Checkout gh-pages branch
        uses: actions/checkout@v4
        with:
          ref: gh-pages
          path: gh-pages

      - name: Update results on gh-pages
        run: |
          # Create ai-evaluation directory if it doesn't exist
          mkdir -p gh-pages/ai-evaluation

          # Copy results with timestamp
          TIMESTAMP=$(date +%Y%m%d_%H%M%S)
          cp -r test-results/* gh-pages/ai-evaluation/

          # Update latest symlink
          cd gh-pages/ai-evaluation
          ln -sfn . latest

          # Generate index page with run history
          python ../../scripts/generate_ai_eval_index.py > index.html

      - name: Commit and push to gh-pages
        run: |
          cd gh-pages
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .
          git commit -m "Update AI evaluation results - $(date +%Y-%m-%d\ %H:%M:%S)" || echo "No changes"
          git push

      - name: Comment on workflow run
        if: always()
        run: |
          echo "## AI Evaluation Results Published" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Results available at: https://curtcox.github.io/Viewer/ai-evaluation/" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Model used: ${{ github.event.inputs.ai_model }}" >> $GITHUB_STEP_SUMMARY
```

**Required Secret:**
- `OPENROUTER_API_KEY`: Add to GitHub repository secrets

**Usage:**
1. Navigate to Actions tab in GitHub
2. Select "AI Evaluation Tests" workflow
3. Click "Run workflow"
4. Choose AI model and optional test pattern
5. Click "Run workflow" button
6. View results at `https://curtcox.github.io/Viewer/ai-evaluation/`

### Results Publishing Structure

**GitHub Pages URL:** `https://curtcox.github.io/Viewer/ai-evaluation/`

**Directory Structure:**
```
gh-pages/
├── index.html                          # Main test results page
├── ai-evaluation/
│   ├── index.html                      # AI evaluation history page
│   ├── latest/                         # Symlink to most recent run
│   ├── 20250211_143022/               # Timestamped run
│   │   ├── ai-eval-report.html        # HTML test report
│   │   ├── ai-eval-results.xml        # JUnit XML
│   │   ├── ai-eval-coverage/          # Coverage report
│   │   │   └── index.html
│   │   └── metadata.json              # Run metadata
│   └── 20250211_120045/               # Previous run
│       └── ...
```

**Index Page Features:**
- List of all evaluation runs with timestamps
- Model used for each run
- Pass/fail summary
- Links to detailed reports
- Trend chart showing pass rates over time
- Filter by model or date range

**Metadata JSON:**
```json
{
  "timestamp": "2025-02-11T14:30:22Z",
  "model": "anthropic/claude-sonnet-4-20250514",
  "total_tests": 9,
  "passed": 8,
  "failed": 1,
  "skipped": 0,
  "duration_seconds": 145,
  "workflow_run_id": "12345678",
  "commit_sha": "abc123def456"
}
```

## Implementation Checklist

### Phase 1: Server Implementation
- [ ] Create `ai_assist.py` server definition
- [ ] Implement OpenRouter API integration
- [ ] Add prompt engineering for context-aware transformations
- [ ] Implement error handling and fallbacks
- [ ] Add configuration variable support
- [ ] Create server template JSON
- [ ] Update boot template to include ai_assist
- [ ] Update alias to point to ai_assist
- [ ] Add documentation for configuration

### Phase 2: Test Infrastructure
- [ ] Create `tests/ai_use_cases/` directory
- [ ] Create `conftest.py` with fixtures
- [ ] Create assertion utilities
- [ ] Create `run_ai_eval_tests.sh` script
- [ ] Create `setup_ai_assist.py` setup script
- [ ] Test local execution workflow

### Phase 3: Test Implementation
- [ ] Implement test 1: Server definition - input validation
- [ ] Implement test 2: Server definition - add logging
- [ ] Implement test 3: Alias editor - query parameters
- [ ] Implement test 4: CID editor - add JSON fields
- [ ] Implement test 5: Upload form - markdown conversion
- [ ] Implement test 6: Import form - CSV to JSON
- [ ] Implement test 7: Secret form - retry config
- [ ] Implement test 8: Variable form - feature flags
- [ ] Implement test 9: Server test card - query filters
- [ ] Verify all tests pass locally

### Phase 4: CI/CD Integration
- [ ] Create `.github/workflows/ai-evaluation.yml`
- [ ] Add `OPENROUTER_API_KEY` to repository secrets
- [ ] Create result summary generation script
- [ ] Create index page generation script
- [ ] Test workflow execution manually
- [ ] Verify results publish to GitHub Pages
- [ ] Create documentation for running on-demand tests

### Phase 5: Documentation
- [ ] Document ai_assist server configuration
- [ ] Document use cases for users
- [ ] Document test execution (local and CI)
- [ ] Add troubleshooting guide
- [ ] Update main README with AI evaluation info

## Success Criteria

1. **Server Functionality:**
   - ai_assist server successfully processes all use case requests
   - Responses are contextually appropriate and accurate
   - Configuration variables work correctly
   - Error handling provides clear feedback

2. **Test Coverage:**
   - All 9 use cases have passing tests
   - Tests run successfully locally and in CI
   - Test results are published to GitHub Pages
   - Tests provide clear failure diagnostics

3. **Documentation:**
   - Clear setup instructions for local and CI
   - Use cases documented for end users
   - Configuration options documented
   - Troubleshooting guide available

4. **User Experience:**
   - AI button works in all 9 locations
   - Response time acceptable (< 30s typical)
   - Results are useful and appropriate
   - Error messages are helpful

## Future Enhancements

1. **One-Shot Runs Enhancement:**
   - Extend `cli.py:make_http_request()` to support POST/PUT/DELETE
   - Add support for JSON request bodies in CLI mode
   - Enable AI evaluation tests to run via CLI without test framework
   - Example: `python main.py --method POST --json '{"request_text":"..."}'  /ai`
   - Benefits: Even simpler test execution, true CLI/HTTP equivalence for AI endpoints
   - Implementation: Modify `handle_http_request()` to accept method and body parameters

2. **Performance Monitoring:**
   - Track AI response times
   - Monitor API costs
   - Alert on degraded performance

3. **Model Comparison:**
   - Run tests against multiple models
   - Compare quality and speed
   - Generate comparison reports

4. **Advanced Use Cases:**
   - Multi-turn conversations
   - Code refactoring suggestions
   - Security vulnerability detection
   - Performance optimization suggestions

5. **User Feedback:**
   - Collect user ratings on AI responses
   - Track acceptance/rejection rates
   - Use feedback to improve prompts

6. **Prompt Optimization:**
   - A/B test different prompt strategies
   - Fine-tune system prompts per use case
   - Implement prompt versioning

## Notes

- Tests require `OPENROUTER_API_KEY` to run - will skip if not available
- Local test runs will incur OpenRouter API costs (minimal for 9 tests)
- CI workflow is on-demand to control costs
- All test results retained for 30 days in GitHub artifacts
- GitHub Pages publishes all historical results for analysis
- Use Case tests are separate from regular integration tests to allow different execution cadence
