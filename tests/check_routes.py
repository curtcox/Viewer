#!/usr/bin/env python3
"""
Test script to verify that the replit_auth.login endpoint is now available
"""

import os
import sys

# Set up environment
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SESSION_SECRET"] = "test-secret-key"
os.environ["REPL_ID"] = "test-repl-id"  # Enable Replit auth for testing

try:
    from app import app

    # Configure app for URL generation outside request context
    app.config["SERVER_NAME"] = "localhost:5000"
    app.config["APPLICATION_ROOT"] = "/"
    app.config["PREFERRED_URL_SCHEME"] = "http"

    with app.app_context():
        print("Testing URL generation for replit_auth.login...")
        try:
            from flask import url_for

            login_url = url_for("replit_auth.login")
            print(f"✅ SUCCESS: replit_auth.login URL = {login_url}")
        except Exception as e:
            print(f"❌ ERROR: {e}")

        print("\nAll routes (showing first 20):")
        count = 0
        for rule in app.url_map.iter_rules():
            if count < 20:
                print(f"  {rule.endpoint}: {rule}")
                count += 1
            if "replit_auth" in rule.endpoint:
                print(f"  *** replit_auth route: {rule.endpoint}: {rule}")

        print(f"\nTotal routes: {len(list(app.url_map.iter_rules()))}")

except Exception as e:
    print(f"❌ Failed to import app: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
