#!/bin/bash
set -e

cat > job-statuses.json << 'EOF'
{
  "ruff": "${{ needs.ruff.result }}",
  "pylint": "${{ needs.pylint.result }}",
  "mypy": "${{ needs.mypy.result }}",
  "radon": "${{ needs.radon.result }}",
  "vulture": "${{ needs.vulture.result }}",
  "python-smells": "${{ needs.python-smells.result }}",
  "shellcheck": "${{ needs.shellcheck.result }}",
  "hadolint": "${{ needs.hadolint.result }}",
  "eslint": "${{ needs.eslint.result }}",
  "stylelint": "${{ needs.stylelint.result }}",
  "uncss": "${{ needs.uncss.result }}",
  "test-index": "${{ needs.test-index.result }}",
  "dead-fixtures": "${{ needs.dead-fixtures.result }}",
  "unit-tests": "${{ needs.unit-tests.result }}",
  "property-tests": "${{ needs.property-tests.result }}",
  "integration-tests": "${{ needs.integration-tests.result }}",
  "gauge-specs": "${{ needs.gauge-specs.result }}"
}
EOF
cat job-statuses.json
