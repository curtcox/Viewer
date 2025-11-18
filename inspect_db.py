#!/usr/bin/env python3
"""
Database inspection script for the Viewer application
"""
from __future__ import annotations

import sys
from datetime import datetime

# Add current directory to path to enable imports from the application
# This must happen before importing app modules
sys.path.insert(0, '.')

# pylint: disable=wrong-import-position
# Rationale: sys.path manipulation required before app imports for standalone script
from app import create_app
from db_access import (
    count_cids,
    count_page_views,
    count_secrets,
    count_servers,
    count_variables,
    get_cid_by_path,
    get_first_cid,
    get_recent_cids,
)

app = create_app()

def inspect_database():
    """Inspect the database and show summary information"""
    with app.app_context():
        print("=" * 60)
        print("DATABASE INSPECTION REPORT")
        print("=" * 60)
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Generated at: {datetime.now()}")
        print()

        # Table counts
        counters = [
            ("CIDs", count_cids),
            ("Page Views", count_page_views),
            ("Servers", count_servers),
            ("Variables", count_variables),
            ("Secrets", count_secrets),
        ]

        print("TABLE COUNTS:")
        print("-" * 30)
        for name, counter in counters:
            count = counter()
            print(f"{name:<20}: {count:>8}")
        print()

        # Recent CIDs
        print("RECENT CID RECORDS (Last 10):")
        print("-" * 50)
        recent_cids = get_recent_cids()
        if recent_cids:
            for cid in recent_cids:
                size_kb = (cid.file_size or 0) / 1024
                print(f"Path: {cid.path}")
                print(f"  Filename: {cid.filename}")
                print(f"  Size: {size_kb:.1f} KB")
                print(f"  Created: {cid.created_at}")
                print()
        else:
            print("No CID records found.")

        # User records are now managed externally; provide guidance instead of data.
        print("USER DIRECTORY:")
        print("-" * 30)
        print("User accounts are no longer stored in the local database.")
        print("Viewer expects authentication and subscription details to be handled externally.")
        print()

def show_cid_details(cid_path: str | None = None):
    """Show detailed information about a specific CID"""
    with app.app_context():
        if cid_path:
            normalized_path = cid_path if cid_path.startswith('/') else f'/{cid_path}'
            cid = get_cid_by_path(normalized_path)
        else:
            cid = get_first_cid()

        if cid:
            print(f"CID DETAILS: {cid.path}")
            print("-" * 40)
            print(f"File Size: {cid.file_size} bytes")
            print(f"Created: {cid.created_at}")
            print(f"Has file data: {cid.file_data is not None}")
            if cid.file_data:
                print(f"File data length: {len(cid.file_data)} bytes")
                # Show first 100 bytes as preview
                preview = cid.file_data[:100]
                try:
                    preview_text = preview.decode('utf-8', errors='replace')
                    print(f"Preview: {repr(preview_text)}")
                except UnicodeDecodeError:
                    print(f"Preview (hex): {preview.hex()}")
        else:
            print("CID not found.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "cid":
            cid_argument = sys.argv[2] if len(sys.argv) > 2 else None
            show_cid_details(cid_argument)
        else:
            print("Usage: python3 inspect_db.py [cid [cid_path]]")
    else:
        inspect_database()
