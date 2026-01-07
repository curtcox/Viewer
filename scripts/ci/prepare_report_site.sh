#!/bin/bash
set -e

python scripts/build-report-site.py \
  --unit-tests-results-artifacts site/unit-tests-results \
  --unit-tests-coverage-artifacts site/unit-tests-coverage \
  --gauge-artifacts site/gauge-specs \
  --integration-artifacts site/integration-tests \
  --property-artifacts site/property-tests \
  --radon-artifacts site/radon \
  --vulture-artifacts site/vulture \
  --python-smells-artifacts site/python-smells \
  --pylint-artifacts site/pylint \
  --pydoclint-artifacts site/pydoclint \
  --shellcheck-artifacts site/shellcheck \
  --hadolint-artifacts site/hadolint \
  --test-index-artifacts site/test-index \
  --cid-validation-artifacts site/cid-validation \
  --ai-eval-artifacts site/ai-eval \
  --job-statuses job-statuses.json \
  --output site
