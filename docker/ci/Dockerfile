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
RUN curl -fsSL https://downloads.gauge.org/stable | sh \
    && /root/.gauge/bin/gauge install python \
    && /root/.gauge/bin/gauge install html-report

# Install Python dependencies used in CI
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt

WORKDIR /workspace
