#!/usr/bin/env python3
"""Migration to remove target_path, match_type, match_pattern, and ignore_case columns from Alias table.

These columns are redundant as all routing information is now derived from the definition field.
This allows aliases to support multi-line and hierarchical definitions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from db_access import get_user_aliases, save_entity
from alias_definition import format_primary_alias_line, parse_alias_definition, AliasDefinitionError
import sqlite3

app = create_app()

def ensure_alias_definitions():
    """Ensure all aliases have valid definitions before removing columns."""

    with app.app_context():
        from models import Alias
        from database import db

        aliases = Alias.query.all()
        print(f"Found {len(aliases)} aliases to check")

        updated = 0
        for alias in aliases:
            # Check if alias already has a definition
            if alias.definition and alias.definition.strip():
                # Verify it's valid
                try:
                    parse_alias_definition(alias.definition, alias_name=alias.name)
                    continue
                except AliasDefinitionError:
                    print(f"  ⚠ Alias '{alias.name}' has invalid definition, will regenerate")

            # Generate definition from columns
            target_path = getattr(alias, 'target_path', None)
            match_type = getattr(alias, 'match_type', 'literal')
            match_pattern = getattr(alias, 'match_pattern', f'/{alias.name}')
            ignore_case = bool(getattr(alias, 'ignore_case', False))

            if not target_path:
                print(f"  ❌ Alias '{alias.name}' has no target_path, skipping")
                continue

            # Create definition from columns
            definition = format_primary_alias_line(
                match_type,
                match_pattern,
                target_path,
                ignore_case=ignore_case,
                alias_name=alias.name,
            )

            alias.definition = definition
            print(f"  ✓ Generated definition for alias '{alias.name}': {definition}")
            updated += 1

        if updated > 0:
            db.session.commit()
            print(f"✓ Updated {updated} aliases with definitions")
        else:
            print("✓ All aliases already have valid definitions")

        return True


def migrate_remove_alias_columns():
    """Remove target_path, match_type, match_pattern, and ignore_case columns from Alias table."""

    with app.app_context():
        # Get absolute database path
        db_path = os.path.join(os.getcwd(), 'instance', 'secureapp.db')

        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return False

        print(f"Migrating database: {db_path}")

        # First, ensure all aliases have definitions
        print("\nStep 1: Ensuring all aliases have valid definitions...")
        if not ensure_alias_definitions():
            return False

        # Connect directly to SQLite to remove columns
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Check current table structure
            cursor.execute("PRAGMA table_info(alias)")
            columns = [column[1] for column in cursor.fetchall()]
            print(f"\nCurrent alias table columns: {columns}")

            columns_to_remove = ['target_path', 'match_type', 'match_pattern', 'ignore_case']
            needs_migration = any(col in columns for col in columns_to_remove)

            if not needs_migration:
                print("✓ Columns already removed, nothing to do")
                conn.close()
                return True

            print("\nStep 2: Removing columns from alias table...")

            # SQLite doesn't support DROP COLUMN directly in older versions
            # We need to recreate the table

            # 1. Create new table with desired structure
            cursor.execute("""
                CREATE TABLE alias_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    definition TEXT,
                    user_id VARCHAR NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME,
                    CONSTRAINT unique_user_alias_name UNIQUE (user_id, name)
                )
            """)
            print("  ✓ Created new alias table structure")

            # 2. Copy data from old table to new table
            cursor.execute("""
                INSERT INTO alias_new (id, name, definition, user_id, created_at, updated_at)
                SELECT id, name, definition, user_id, created_at, updated_at
                FROM alias
            """)
            print("  ✓ Copied data to new table")

            # 3. Drop old table
            cursor.execute("DROP TABLE alias")
            print("  ✓ Dropped old alias table")

            # 4. Rename new table to original name
            cursor.execute("ALTER TABLE alias_new RENAME TO alias")
            print("  ✓ Renamed new table to 'alias'")

            # 5. Recreate indexes
            cursor.execute("CREATE INDEX ix_alias_name ON alias (name)")
            print("  ✓ Recreated index on name column")

            conn.commit()
            print("\n✓ Successfully removed columns from alias table")
            conn.close()

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            conn.close()
            return False

if __name__ == '__main__':
    try:
        print("=" * 60)
        print("Alias Column Removal Migration")
        print("=" * 60)
        print("\nThis migration will:")
        print("  1. Ensure all aliases have valid definitions")
        print("  2. Remove target_path, match_type, match_pattern, ignore_case columns")
        print("  3. All routing data will be derived from the definition field")
        print()

        success = migrate_remove_alias_columns()
        if success:
            print("\n" + "=" * 60)
            print("✅ Migration completed successfully!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ Migration failed!")
            print("=" * 60)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
