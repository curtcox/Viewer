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

**Technology:** Pytest + Selenium WebDriver (consistent with existing integration tests)

**Fixtures Required:** (`conftest.py`)
```python
import pytest
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture(scope="session")
def requires_openrouter_api_key():
    """Skip tests if OPENROUTER_API_KEY not available."""
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set - skipping AI evaluation tests")

@pytest.fixture
def driver():
    """WebDriver instance for browser automation."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

@pytest.fixture
def ai_test_server(app_client):
    """Ensure ai_assist server is enabled and configured."""
    # Setup ai_assist server for testing
    # Configure with test API key
    yield
    # Cleanup after tests

@pytest.fixture
def interaction_history():
    """Track interaction history for debugging failed tests."""
    history = []
    yield history
    # Save history if test fails
```

### Test Template

Each test follows this pattern:

```python
def test_use_case_name(driver, ai_test_server, requires_openrouter_api_key):
    """
    Test Case: [Description]

    Given: [Initial state]
    When: [User action]
    Then: [Expected outcome]
    """
    # 1. Navigate to page
    driver.get("http://localhost:5000/target/page")

    # 2. Set initial content
    text_area = driver.find_element(By.ID, "target-field")
    text_area.clear()
    text_area.send_keys(INITIAL_CONTENT)

    # 3. Enter AI request
    ai_request_input = driver.find_element(By.ID, "ai-request-input")
    ai_request_input.send_keys(USER_REQUEST)

    # 4. Click AI button
    ai_button = driver.find_element(By.CLASS_NAME, "ai-action-button")
    ai_button.click()

    # 5. Wait for response
    wait = WebDriverWait(driver, 30)  # AI responses may take time
    wait.until(lambda d: d.find_element(By.ID, "ai-output").text != "")

    # 6. Verify result
    result = driver.find_element(By.ID, "ai-output").text

    # Assertions
    assert_ai_output_valid(result)
    assert_original_content_preserved(result, INITIAL_CONTENT)
    assert_requested_change_applied(result, USER_REQUEST)

    # 7. Verify no errors
    assert "error" not in result.lower()
```

### Individual Test Specifications

#### Test 1: Server Definition - Input Validation

**File:** `tests/ai_use_cases/test_server_definition_editor.py::test_add_input_validation`

**Setup:**
- Navigate to `/server/edit?name=hello_world`
- Ensure server exists with simple greeting code
- Clear any existing AI history

**Execution:**
1. Set definition field to Use Case 1 initial content
2. Enter AI request: "Add input validation to reject empty names"
3. Click AI action button
4. Wait for AI response (max 30s)

**Assertions:**
- Response contains `if not name or not name.strip()`
- Response contains `status": 400` or similar error handling
- Response contains original greeting logic
- Valid Python syntax (use `ast.parse()` to verify)
- Function signature preserved: `def main(name="World")`

**Failure Handling:**
- Save interaction history to test artifacts
- Screenshot the form state
- Log the AI response for debugging

---

#### Test 2: Server Definition - Add Logging

**File:** `tests/ai_use_cases/test_server_definition_editor.py::test_add_logging`

**Setup:**
- Navigate to `/server/edit?name=data_processor`
- Create server if not exists

**Execution:**
1. Set definition to Use Case 2 initial content
2. AI request: "Add logging before and after processing"
3. Submit and wait for response

**Assertions:**
- `import logging` present
- At least 2 `logging.info()` or `logging.debug()` calls
- Original processing logic preserved (`.upper()` operation)
- Valid Python syntax
- Function signature preserved

---

#### Test 3: Alias Definition - Add Query Parameters

**File:** `tests/ai_use_cases/test_alias_editor.py::test_add_query_parameters`

**Setup:**
- Navigate to `/alias/edit?name=hello`
- Ensure alias exists

**Execution:**
1. Set alias definition to `/servers/hello_world`
2. AI request: "Add query parameters for name and greeting style"
3. Submit and wait

**Assertions:**
- Original path `/servers/hello_world` preserved
- Contains `?` character
- Contains `name=` parameter
- Contains `style=` parameter
- Valid URL format (no invalid characters)
- Length < 500 characters

---

#### Test 4: CID Editor - Add JSON Fields

**File:** `tests/ai_use_cases/test_cid_editor.py::test_add_email_field`

**Setup:**
- Create test CID with user data
- Navigate to `/cid/edit?id={cid}`

**Execution:**
1. Set content to Use Case 4 initial JSON
2. AI request: "Add an email field to each user"
3. Submit and wait

**Assertions:**
- Valid JSON structure (use `json.loads()`)
- All users have `email` field
- Original fields preserved (`name`, `role`)
- Email format plausible (contains `@`)
- User count unchanged (2 users)

---

#### Test 5: Upload Form - Markdown Conversion

**File:** `tests/ai_use_cases/test_upload_form.py::test_convert_to_markdown_list`

**Setup:**
- Navigate to `/upload`

**Execution:**
1. Set text content to Use Case 5 initial content
2. AI request: "Convert to markdown list with descriptions"
3. Submit and wait

**Assertions:**
- Contains markdown list markers (`-` or `*` or `1.`)
- Contains markdown bold markers (`**`)
- All original items present (Fast Performance, Easy to Use, Secure)
- Format is valid markdown
- Descriptions added (result longer than input)

---

#### Test 6: Import Form - CSV to JSON

**File:** `tests/ai_use_cases/test_import_form.py::test_csv_to_json_conversion`

**Setup:**
- Navigate to `/import`

**Execution:**
1. Set import text to Use Case 6 CSV content
2. AI request: "Convert to JSON array of objects"
3. Submit and wait

**Assertions:**
- Valid JSON (parse with `json.loads()`)
- Structure is array of objects
- 3 objects present (one per CSV row)
- All fields present: name, status, priority
- Field names are lowercase
- All data values preserved

---

#### Test 7: Secret Form - Add Retry Config

**File:** `tests/ai_use_cases/test_secret_form.py::test_add_retry_configuration`

**Setup:**
- Navigate to `/secret/edit?name=API_CONFIG`
- Create secret if needed

**Execution:**
1. Set value to Use Case 7 initial JSON
2. AI request: "Add retry configuration with 3 attempts and exponential backoff"
3. Submit and wait

**Assertions:**
- Valid JSON structure
- Original fields preserved (`endpoint`, `timeout`)
- `retry` object added
- `retry.max_attempts` = 3
- `retry.backoff_strategy` = "exponential"
- Additional retry fields present (delay, etc.)

---

#### Test 8: Variable Form - Add Feature Flags

**File:** `tests/ai_use_cases/test_variable_form.py::test_add_feature_flags`

**Setup:**
- Navigate to `/variable/edit?name=APP_CONFIG`
- Create variable if needed

**Execution:**
1. Set value to Use Case 8 initial JSON
2. AI request: "Add feature flags for dark mode and experimental features"
3. Submit and wait

**Assertions:**
- Valid JSON structure
- Original fields preserved
- `features` object added
- `features.dark_mode` is boolean
- `features.experimental_features` is boolean
- Feature flags are reasonable (true/false, not random strings)

---

#### Test 9: Server Test Card - Add Query Filters

**File:** `tests/ai_use_cases/test_server_test_card.py::test_add_query_filters`

**Setup:**
- Navigate to `/server/test?name=api_endpoint`
- Ensure test server exists

**Execution:**
1. Set query params to `page=1&limit=10`
2. AI request: "Add filtering by status and sorting by date descending"
3. Submit and wait

**Assertions:**
- Original params preserved (`page=1`, `limit=10`)
- Contains `status=` parameter
- Contains `sort=` parameter (or `order=`)
- Valid query string format
- No duplicate parameters
- Properly URL encoded

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
# Run AI evaluation tests locally

set -e

echo "Running AI Evaluation Tests"
echo "============================="

# 1. Check for OpenRouter API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY environment variable not set"
    echo "Set it with: export OPENROUTER_API_KEY=your_key_here"
    exit 1
fi

# 2. Ensure ai_assist server is configured
echo "Configuring ai_assist server..."
python scripts/setup_ai_assist.py

# 3. Start application in test mode
echo "Starting application..."
export FLASK_ENV=testing
export AI_MODEL="${AI_MODEL:-anthropic/claude-sonnet-4-20250514}"
python run.py &
APP_PID=$!

# Wait for app to start
sleep 5

# 4. Run tests with coverage
echo "Running AI evaluation tests..."
pytest tests/ai_use_cases/ \
    --verbose \
    --capture=no \
    --tb=short \
    --junit-xml=test-results/ai-eval-results.xml \
    --html=test-results/ai-eval-report.html \
    --self-contained-html \
    --cov=reference_templates.servers.definitions.ai_assist \
    --cov-report=html:test-results/ai-eval-coverage

# 5. Cleanup
kill $APP_PID

echo ""
echo "============================="
echo "Test Results:"
echo "  - JUnit XML: test-results/ai-eval-results.xml"
echo "  - HTML Report: test-results/ai-eval-report.html"
echo "  - Coverage: test-results/ai-eval-coverage/index.html"
echo "============================="
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
```

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
          pip install pytest pytest-html pytest-cov selenium

      - name: Install Chrome and ChromeDriver
        run: |
          sudo apt-get update
          sudo apt-get install -y chromium-browser chromium-chromedriver

      - name: Configure ai_assist server
        run: |
          python scripts/setup_ai_assist.py

      - name: Run AI evaluation tests
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          AI_MODEL: ${{ github.event.inputs.ai_model }}
        run: |
          # Start application
          python run.py &
          APP_PID=$!
          sleep 5

          # Run tests
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

          # Cleanup
          kill $APP_PID

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

1. **Performance Monitoring:**
   - Track AI response times
   - Monitor API costs
   - Alert on degraded performance

2. **Model Comparison:**
   - Run tests against multiple models
   - Compare quality and speed
   - Generate comparison reports

3. **Advanced Use Cases:**
   - Multi-turn conversations
   - Code refactoring suggestions
   - Security vulnerability detection
   - Performance optimization suggestions

4. **User Feedback:**
   - Collect user ratings on AI responses
   - Track acceptance/rejection rates
   - Use feedback to improve prompts

5. **Prompt Optimization:**
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
