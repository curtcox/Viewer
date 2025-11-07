#!/usr/bin/env python3

import os
import sqlite3
import sys

# Add script directory to path to enable imports from the application
# This must happen before importing app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# pylint: disable=wrong-import-position
# Rationale: sys.path manipulation required before app imports for standalone migration script
from app import create_app
from cid_utils import save_server_definition_as_cid
from db_access import get_all_servers, save_entity

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
            servers = get_all_servers()
            print(f"Found {len(servers)} existing servers to update")

            updated_servers = 0
            for server in servers:
                if not server.definition_cid and server.definition:
                    # Generate CID for existing definition
                    cid = save_server_definition_as_cid(server.definition, server.user_id)
                    server.definition_cid = cid
                    print(f"✓ Updated server '{server.name}' with CID: {cid}")
                    save_entity(server)
                    updated_servers += 1

            print(f"✓ Updated {updated_servers} servers with CIDs")

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
