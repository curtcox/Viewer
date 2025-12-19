# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.gauge/bin:${PATH}"

# Install system dependencies, including Node.js for JavaScript-based GitHub Actions
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        gnupg \
        jq \
        unzip \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libxss1 \
        libxtst6 \
        libgbm1 \
        libgtk-3-0 \
        libasound2 \
        fonts-liberation \
    && curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource-setup.sh \
    && bash /tmp/nodesource-setup.sh \
    && rm /tmp/nodesource-setup.sh \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Use bash with pipefail so pipelines inside RUN directives fail early.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Gauge CLI and required plugins
ARG GAUGE_VERSION=1.5.6
ARG GAUGE_DIST_URL="https://github.com/getgauge/gauge/releases/download/v${GAUGE_VERSION}/gauge-${GAUGE_VERSION}-linux.x86_64.zip"
RUN set -eux; \
    curl -fsSL "${GAUGE_DIST_URL}" -o /tmp/gauge.zip; \
    unzip /tmp/gauge.zip -d /tmp/gauge-dist; \
    if GAUGE_DIR="$(find /tmp/gauge-dist -maxdepth 1 -mindepth 1 -type d -name 'gauge-*' | head -n 1)" && [ -n "${GAUGE_DIR}" ]; then \
        mv "${GAUGE_DIR}" /opt/gauge; \
    elif [ -f /tmp/gauge-dist/gauge ]; then \
        install -Dm755 /tmp/gauge-dist/gauge /opt/gauge/bin/gauge; \
    else \
        echo "Unexpected Gauge archive layout" >&2; \
        exit 1; \
    fi; \
    ln -s /opt/gauge/bin/gauge /usr/local/bin/gauge; \
    rm -rf /tmp/gauge.zip /tmp/gauge-dist; \
    gauge install python; \
    gauge install html-report

# Install Python dependencies used in CI
COPY requirements.txt /tmp/requirements.txt
# hadolint ignore=DL3013
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt \
    && python -m pip install hypothesis pytest

# Pre-download Chromium so container users (and any jobs that retain /root as
# $HOME) already have a browser binary before Gauge runs. GitHub Actions swaps
# HOME to /github/home at runtime, so the workflow reruns the installer there.
RUN pyppeteer-install

WORKDIR /workspace
