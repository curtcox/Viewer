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

# 3. Detect available pytest plugins
PYTEST_ARGS="tests/ai_use_cases/ --verbose --tb=short"

# Create test-results directory if needed
mkdir -p test-results

# Check for pytest-html plugin
if python -c "import pytest_html" 2>/dev/null; then
    PYTEST_ARGS="$PYTEST_ARGS --html=test-results/ai-eval-report.html --self-contained-html"
    HAS_HTML=true
else
    echo "Note: pytest-html not installed (optional - install with: pip install pytest-html)"
    HAS_HTML=false
fi

# Check for pytest-cov plugin
if python -c "import pytest_cov" 2>/dev/null; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=reference_templates.servers.definitions.ai_assist"
    PYTEST_ARGS="$PYTEST_ARGS --cov-report=html:test-results/ai-eval-coverage"
    PYTEST_ARGS="$PYTEST_ARGS --cov-report=term-missing"
    HAS_COV=true
else
    echo "Note: pytest-cov not installed (optional - install with: pip install pytest-cov)"
    HAS_COV=false
fi

# Always generate JUnit XML (built into pytest)
PYTEST_ARGS="$PYTEST_ARGS --junit-xml=test-results/ai-eval-results.xml"

# 4. Run tests
# Note: No need to start web server - tests use memory_client fixture
echo ""
echo "Running AI evaluation tests..."
pytest $PYTEST_ARGS

echo ""
echo "========================================"
echo "Test Results:"
echo "  - JUnit XML: test-results/ai-eval-results.xml"
if [ "$HAS_HTML" = true ]; then
    echo "  - HTML Report: test-results/ai-eval-report.html"
fi
if [ "$HAS_COV" = true ]; then
    echo "  - Coverage: test-results/ai-eval-coverage/index.html"
fi
echo "========================================"
