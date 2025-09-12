#!/usr/bin/env python3
"""
Database inspection script for the Viewer application
"""
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, '.')

# Import Flask app and models
from app import app, db
from models import User, CID, PageView, Server, Variable, Secret, Payment, TermsAcceptance, Invitation

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
        tables = [
            ("Users", User),
            ("CIDs", CID),
            ("Page Views", PageView),
            ("Servers", Server),
            ("Variables", Variable),
            ("Secrets", Secret),
            ("Payments", Payment),
            ("Terms Acceptances", TermsAcceptance),
            ("Invitations", Invitation)
        ]
        
        print("TABLE COUNTS:")
        print("-" * 30)
        for name, model in tables:
            count = model.query.count()
            print(f"{name:<20}: {count:>8}")
        print()
        
        # Recent CIDs
        print("RECENT CID RECORDS (Last 10):")
        print("-" * 50)
        recent_cids = CID.query.order_by(CID.created_at.desc()).limit(10).all()
        if recent_cids:
            for cid in recent_cids:
                size_kb = (cid.file_size or 0) / 1024
                print(f"Path: {cid.path}")
                print(f"  Filename: {cid.filename}")
                print(f"  Size: {size_kb:.1f} KB")
                print(f"  Created: {cid.created_at}")
                print(f"  User: {cid.uploaded_by_user_id}")
                print()
        else:
            print("No CID records found.")
        
        # Users summary
        print("USERS SUMMARY:")
        print("-" * 30)
        users = User.query.all()
        if users:
            for user in users:
                print(f"ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Name: {user.first_name} {user.last_name}")
                print(f"  Paid: {user.is_paid}")
                print(f"  Terms Accepted: {user.current_terms_accepted}")
                print(f"  Uploads: {len(user.uploads)}")
                print()
        else:
            print("No users found.")

def show_cid_details(cid_path=None):
    """Show detailed information about a specific CID"""
    with app.app_context():
        if cid_path:
            if not cid_path.startswith('/'):
                cid_path = f'/{cid_path}'
            cid = CID.query.filter_by(path=cid_path).first()
        else:
            cid = CID.query.first()
        
        if cid:
            print(f"CID DETAILS: {cid.path}")
            print("-" * 40)
            print(f"Filename: {cid.filename}")
            print(f"File Size: {cid.file_size} bytes")
            print(f"Created: {cid.created_at}")
            print(f"Uploaded by: {cid.uploaded_by_user_id}")
            print(f"Has file data: {cid.file_data is not None}")
            if cid.file_data:
                print(f"File data length: {len(cid.file_data)} bytes")
                # Show first 100 bytes as preview
                preview = cid.file_data[:100]
                try:
                    preview_text = preview.decode('utf-8', errors='replace')
                    print(f"Preview: {repr(preview_text)}")
                except:
                    print(f"Preview (hex): {preview.hex()}")
        else:
            print("CID not found.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "cid":
            cid_path = sys.argv[2] if len(sys.argv) > 2 else None
            show_cid_details(cid_path)
        else:
            print("Usage: python3 inspect_db.py [cid [cid_path]]")
    else:
        inspect_database()
