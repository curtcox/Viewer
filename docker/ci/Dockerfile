# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.gauge/bin:${PATH}"

# Install system dependencies, including Node.js for JavaScript-based GitHub Actions
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        gnupg \
        unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Gauge CLI and required plugins
ARG GAUGE_VERSION=1.5.6
ARG GAUGE_DIST_URL="https://github.com/getgauge/gauge/releases/download/v${GAUGE_VERSION}/gauge-${GAUGE_VERSION}-linux.x86_64.zip"
RUN curl -fsSL "${GAUGE_DIST_URL}" -o /tmp/gauge.zip \
    && unzip /tmp/gauge.zip -d /tmp/gauge-dist \
    && GAUGE_DIR="$(find /tmp/gauge-dist -maxdepth 1 -mindepth 1 -type d -name 'gauge-*' | head -n 1)" \
    && [ -n "${GAUGE_DIR}" ] \
    && mv "${GAUGE_DIR}" /opt/gauge \
    && ln -s /opt/gauge/bin/gauge /usr/local/bin/gauge \
    && rm -rf /tmp/gauge.zip /tmp/gauge-dist \
    && gauge install python \
    && gauge install html-report

# Install Python dependencies used in CI
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt

WORKDIR /workspace
