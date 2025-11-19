#!/bin/bash
set -e

python scripts/build-report-site.py \
  --unit-tests-artifacts site/unit-tests \
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
  --job-statuses job-statuses.json \
  --output site
