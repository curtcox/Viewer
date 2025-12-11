# AI Evaluation Tests

This directory contains AI evaluation tests that verify the behavior of AI-assisted features in the application.

## Running AI Eval Tests

The AI evaluation tests require an OpenRouter API key to run:

```bash
export OPENROUTER_API_KEY=your_key_here
./run_ai_eval_tests.sh
```

## Test Reports

After running the tests, HTML reports are generated in `test-results/ai-eval-reports/`:

- **Index page**: `test-results/ai-eval-reports/index.html` - Overview of all test cases with pass/fail status
- **Detail pages**: Individual HTML files for each test showing:
  - Test source code with syntax highlighting
  - AI request details (prompt, original text, context)
  - AI response (updated text or error)
  - Test status and metadata

## Viewing Reports

### Locally

After running tests, you can view the reports:

1. Via filesystem: Open `test-results/ai-eval-reports/index.html` in a browser
2. Via Flask app: Navigate to `/source/test-results/ai-eval-reports/index.html` in the running application

### On Deployed Site

Reports can be included in the GitHub Pages deployment by:

1. Running AI eval tests and uploading artifacts in a workflow
2. Passing `--ai-eval-artifacts` to `scripts/build-report-site.py`
3. Reports will be available at `https://curtcox.github.io/Viewer/ai-eval/index.html`

## Test Structure

Each test case:

1. Sets up an AI request with context (original text, prompt, form type)
2. Makes a POST request to `/ai` endpoint
3. Validates the AI response
4. Records all interactions to JSON files in `test-results/ai-interactions/`

The `generate_ai_eval_reports.py` script processes these JSON files to create the HTML reports.

## Adding New Tests

To add a new AI evaluation test:

1. Create a test function in `tests/ai_use_cases/test_*.py`
2. Use the `ai_interaction_tracker` fixture to record interactions
3. Follow the existing test patterns for making AI requests
4. The test will automatically appear in the generated reports

Example:

```python
def test_my_use_case(memory_client, requires_openrouter_api_key, ai_interaction_tracker):
    """Test AI does something useful."""
    payload = {
        'request_text': 'Do something useful',
        'original_text': 'original content',
        'target_label': 'description',
        'context_data': {},
        'form_summary': {}
    }
    
    response = memory_client.post('/ai', json=payload)
    ai_interaction_tracker(payload, response.get_json(), response.status_code)
    
    # Assert expected behavior
    assert response.status_code == 200
    # ... more assertions
```
