#!/bin/bash
set -e

HADOLINT_VERSION=2.12.0
HADOLINT_URL="https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-x86_64"

echo "Downloading hadolint v${HADOLINT_VERSION}..."
if ! wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -t 3 -q "${HADOLINT_URL}" -O hadolint; then
  echo "Error: Failed to download hadolint from ${HADOLINT_URL}" >&2
  exit 1
fi

if [ ! -f hadolint ] || [ ! -s hadolint ]; then
  echo "Error: Downloaded hadolint file is missing or empty" >&2
  exit 1
fi

chmod +x hadolint
sudo mv hadolint /usr/local/bin/hadolint
echo "Hadolint installed successfully"
