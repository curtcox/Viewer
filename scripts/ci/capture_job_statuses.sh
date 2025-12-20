#!/bin/bash
set -e

cat > job-statuses.json << EOF
{
  "ruff": "${RUFF_STATUS}",
  "pylint": "${PYLINT_STATUS}",
  "mypy": "${MYPY_STATUS}",
  "pydoclint": "${PYDOCLINT_STATUS}",
  "radon": "${RADON_STATUS}",
  "vulture": "${VULTURE_STATUS}",
  "python-smells": "${PYTHON_SMELLS_STATUS}",
  "shellcheck": "${SHELLCHECK_STATUS}",
  "hadolint": "${HADOLINT_STATUS}",
  "eslint": "${ESLINT_STATUS}",
  "stylelint": "${STYLELINT_STATUS}",
  "uncss": "${UNCSS_STATUS}",
  "test-index": "${TEST_INDEX_STATUS}",
  "cid-validation": "${CID_VALIDATION_STATUS}",
  "dead-fixtures": "${DEAD_FIXTURES_STATUS}",
  "unit-tests": "${UNIT_TESTS_STATUS}",
  "property-tests": "${PROPERTY_TESTS_STATUS}",
  "integration-tests": "${INTEGRATION_TESTS_STATUS}",
  "gauge-specs": "${GAUGE_SPECS_STATUS}",
  "ai-eval": "${AI_EVAL_STATUS}"
}
EOF
cat job-statuses.json
