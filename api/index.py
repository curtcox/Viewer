"""
Vercel serverless function entry point.

This module provides the WSGI application interface required by Vercel's
Python runtime for deploying the Flask application.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from the main app
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import create_app

# Create Flask application instance
app = create_app()
