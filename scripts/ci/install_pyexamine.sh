#!/bin/bash
set -e

# Pin to specific commit to avoid supply-chain risks from main branch changes
# Commit 1c9360462281d897ab429878139e07ae3f98f104 (2025-01-27): README rename, stable state
git clone https://github.com/KarthikShivasankar/python_smells_detector.git /tmp/python_smells_detector
cd /tmp/python_smells_detector
git checkout 1c9360462281d897ab429878139e07ae3f98f104
cd -
python -m pip install --disable-pip-version-check -e /tmp/python_smells_detector
