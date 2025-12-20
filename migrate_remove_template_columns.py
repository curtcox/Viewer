"""Migration script to remove template columns and migrate to templates variable.

This script:
1. Queries all entities where template=True
2. Builds a global templates JSON structure
3. Stores it as the global 'templates' variable
4. Drops the template columns from database tables

Usage:
    python migrate_remove_template_columns.py
"""

import json
import os
import sys
from datetime import datetime, timezone

# Configure environment before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///instance/viewer.db")
os.environ.setdefault("SESSION_SECRET", "migration-secret-key")

from app import app
from database import db
from models import Variable
from sqlalchemy import text


def query_template_entities():
    """Query all template entities from the database before migration.

    Returns:
        Templates dict keyed by entity type.
    """
    print("Querying existing template entities...")

    templates = {"aliases": {}, "servers": {}, "variables": {}, "secrets": {}}

    # Query each entity type for templates
    # Note: We query directly with SQL since the models no longer have template column

    # Aliases
    try:
        result = db.session.execute(
            text(
                "SELECT id, name, definition, created_at FROM alias WHERE template = 1"
            )
        )
        rows = list(result)
        for row in rows:
            templates["aliases"][row.name] = {
                "name": row.name,
                "description": "Migrated from database template",
                "target_path": row.definition or "",
                "metadata": {
                    "created": row.created_at.isoformat()
                    if row.created_at
                    else datetime.now(timezone.utc).isoformat(),
                    "migrated": True,
                    "original_id": row.id,
                },
            }
        print(f"  Found {len(rows)} template aliases")
    except Exception as e:
        print(f"  No template column in alias table (already migrated?) - {e}")

    # Servers
    try:
        result = db.session.execute(
            text(
                "SELECT id, name, definition, created_at FROM server WHERE template = 1"
            )
        )
        rows = list(result)
        for row in rows:
            templates["servers"][row.name] = {
                "name": row.name,
                "description": "Migrated from database template",
                "definition": row.definition or "",
                "metadata": {
                    "created": row.created_at.isoformat()
                    if row.created_at
                    else datetime.now(timezone.utc).isoformat(),
                    "migrated": True,
                    "original_id": row.id,
                },
            }
        print(f"  Found {len(rows)} template servers")
    except Exception as e:
        print(f"  No template column in server table (already migrated?) - {e}")

    # Variables
    try:
        result = db.session.execute(
            text(
                "SELECT id, name, definition, created_at FROM variable WHERE template = 1"
            )
        )
        rows = list(result)
        for row in rows:
            # Skip the templates variable itself
            if row.name == "templates":
                continue
            templates["variables"][row.name] = {
                "name": row.name,
                "description": "Migrated from database template",
                "definition": row.definition or "",
                "metadata": {
                    "created": row.created_at.isoformat()
                    if row.created_at
                    else datetime.now(timezone.utc).isoformat(),
                    "migrated": True,
                    "original_id": row.id,
                },
            }
        print(f"  Found {len(rows)} template variables")
    except Exception as e:
        print(f"  No template column in variable table (already migrated?) - {e}")

    # Secrets
    try:
        result = db.session.execute(
            text(
                "SELECT id, name, definition, created_at FROM secret WHERE template = 1"
            )
        )
        rows = list(result)
        for row in rows:
            templates["secrets"][row.name] = {
                "name": row.name,
                "description": "Migrated from database template",
                "value": row.definition or "",
                "metadata": {
                    "created": row.created_at.isoformat()
                    if row.created_at
                    else datetime.now(timezone.utc).isoformat(),
                    "migrated": True,
                    "original_id": row.id,
                },
            }
        print(f"  Found {len(rows)} template secrets")
    except Exception as e:
        print(f"  No template column in secret table (already migrated?) - {e}")

    return templates


def create_templates_variable(templates):
    """Create or update the global templates variable."""
    print("\nCreating templates variable...")

    # Check if any templates exist
    total_templates = sum(
        len(templates[entity_type])
        for entity_type in ["aliases", "servers", "variables", "secrets"]
    )

    if total_templates == 0:
        print("  No templates to migrate")
        return

    # Convert to JSON
    templates_json = json.dumps(templates, indent=2)

    # Check if templates variable already exists
    existing = Variable.query.filter_by(name="templates").first()

    if existing:
        print(f"  Updating existing templates variable ({total_templates} templates)")
        existing.definition = templates_json
        existing.updated_at = datetime.now(timezone.utc)
    else:
        print(f"  Creating new templates variable ({total_templates} templates)")
        new_var = Variable(name="templates", definition=templates_json, enabled=True)
        db.session.add(new_var)

    db.session.commit()
    print("Templates variable created successfully")


def drop_template_columns():
    """Drop template columns from all entity tables.

    Note: This uses raw SQL and should be tested carefully.
    """
    print("\nDropping template columns from tables...")

    tables = ["alias", "server", "variable", "secret"]

    for table in tables:
        try:
            # Check if column exists first
            result = db.session.execute(text(f"PRAGMA table_info({table})"))
            rows = list(result)
            columns = [row[1] for row in rows]

            if "template" in columns:
                # SQLite doesn't support DROP COLUMN directly in older versions
                # We need to use the ALTER TABLE ... DROP COLUMN syntax (SQLite 3.35.0+)
                try:
                    db.session.execute(
                        text(f"ALTER TABLE {table} DROP COLUMN template")
                    )
                    db.session.commit()
                    print(f"  Dropped template column from {table} table")
                except Exception as e:
                    print(
                        f"  Warning: Could not drop template column from {table}: {e}"
                    )
                    print(
                        "  This is expected for SQLite < 3.35.0. Column will remain but is unused."
                    )
                    db.session.rollback()
            else:
                print(f"  Template column already removed from {table} table")

        except Exception as e:
            print(f"  Error processing {table} table: {e}")
            db.session.rollback()


def main():
    """Run the migration."""
    print("=" * 70)
    print("Template System Migration")
    print("=" * 70)
    print("\nThis script will:")
    print("1. Find all entities marked as templates (template=True)")
    print("2. Create a 'templates' variable with JSON configuration")
    print("3. Drop the template columns from database tables")
    print("\nWARNING: Make sure you have a database backup before proceeding!")
    print("=" * 70)

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Migration cancelled.")
        return 1

    with app.app_context():
        try:
            # Step 1: Query template entities
            templates = query_template_entities()

            # Step 2: Create templates variable
            create_templates_variable(templates)

            # Step 3: Drop template columns
            drop_template_columns()

            print("\n" + "=" * 70)
            print("Migration completed successfully!")
            print("=" * 70)
            return 0

        except Exception as e:
            print(f"\nError during migration: {e}")
            import traceback

            traceback.print_exc()
            db.session.rollback()
            return 1


if __name__ == "__main__":
    sys.exit(main())
