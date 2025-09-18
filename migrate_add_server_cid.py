#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import db
from models import Server
from cid_utils import save_server_definition_as_cid
import sqlite3

app = create_app()

def migrate_add_server_cid():
    """Add definition_cid column to Server table and populate existing servers"""
    
    with app.app_context():
        # Get absolute database path
        db_path = os.path.join(os.getcwd(), 'instance', 'secureapp.db')
        
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return False
        
        print(f"Migrating database: {db_path}")
        
        # Connect directly to SQLite to add column
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if column already exists
            cursor.execute("PRAGMA table_info(server)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'definition_cid' in columns:
                print("✓ Column definition_cid already exists")
                conn.close()
                return True
            
            # Add the new column
            cursor.execute("ALTER TABLE server ADD COLUMN definition_cid VARCHAR(255)")
            conn.commit()
            print("✓ Added definition_cid column to server table")
            
            # Create index on the new column
            cursor.execute("CREATE INDEX ix_server_definition_cid ON server (definition_cid)")
            conn.commit()
            print("✓ Created index on definition_cid column")
            
            conn.close()
            
            # Now populate existing servers with CIDs
            servers = Server.query.all()
            print(f"Found {len(servers)} existing servers to update")
            
            for server in servers:
                if not server.definition_cid and server.definition:
                    # Generate CID for existing definition
                    cid = save_server_definition_as_cid(server.definition, server.user_id)
                    server.definition_cid = cid
                    print(f"✓ Updated server '{server.name}' with CID: {cid}")
            
            db.session.commit()
            print(f"✓ Updated {len(servers)} servers with CIDs")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            conn.close()
            return False

if __name__ == '__main__':
    try:
        success = migrate_add_server_cid()
        if success:
            print("✅ Migration completed successfully!")
        else:
            print("❌ Migration failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
