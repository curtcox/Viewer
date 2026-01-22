#!/bin/bash
set -e

# Use PUBLIC_BASE_URL from environment, or default
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://curtcox.github.io/Viewer}"

# Use GIT_SHA from environment if provided
GIT_SHA_ARG=""
if [ -n "${GIT_SHA:-}" ]; then
  GIT_SHA_ARG="--git-sha $GIT_SHA"
fi

python scripts/build-report-site.py \
  --unit-tests-results-artifacts artifacts/unit-tests-results \
  --unit-tests-coverage-artifacts artifacts/unit-tests-coverage \
  --gauge-artifacts artifacts/gauge-specs \
  --integration-artifacts artifacts/integration-tests \
  --hypothesis-artifacts artifacts/hypothesis-tests \
  --radon-artifacts artifacts/radon \
  --vulture-artifacts artifacts/vulture \
  --python-smells-artifacts artifacts/python-smells \
  --pylint-artifacts artifacts/pylint \
  --pydoclint-artifacts artifacts/pydoclint \
  --shellcheck-artifacts artifacts/shellcheck \
  --hadolint-artifacts artifacts/hadolint \
  --test-index-artifacts artifacts/test-index \
  --cid-validation-artifacts artifacts/cid-validation \
  --ai-eval-artifacts artifacts/ai-eval \
  --job-statuses job-statuses.json \
  --public-base-url "$PUBLIC_BASE_URL" \
  $GIT_SHA_ARG \
  --output site

# Copy job-statuses.json to site directory for later extraction
if [ -f job-statuses.json ]; then
  cp job-statuses.json site/job-statuses.json
  echo "Copied job-statuses.json to site directory"
fi

