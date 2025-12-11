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
