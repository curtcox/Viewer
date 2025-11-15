"""Manual test script for boot CID import functionality.

This script can be run to manually test the boot CID import feature.
Run with: python test_boot_cid_manual.py
"""

import json
import sys

from app import create_app, db
from boot_cid_importer import (
    extract_cid_references_from_payload,
    import_boot_cid,
    verify_boot_cid_dependencies,
)
from cid_utils import generate_cid
from db_access import create_cid_record
from models import Alias, Server


def test_boot_cid_import():
    """Test the boot CID import functionality."""
    print("Creating test app...")
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })

    with app.app_context():
        db.create_all()

        print("\n1. Testing CID reference extraction...")
        test_payload = {
            'version': 6,
            'aliases': 'test_cid_1',
            'servers': 'test_cid_2',
            'cid_values': {
                'test_cid_3': 'content3',
            }
        }
        refs = extract_cid_references_from_payload(test_payload)
        print(f"   Found {len(refs)} CID references")
        assert len(refs) > 0, "Should find CID references"

        print("\n2. Testing missing CID detection...")
        # Create alias content
        aliases_data = [{'name': 'test-alias', 'target': '/test'}]
        aliases_content = json.dumps(aliases_data).encode('utf-8')
        aliases_cid = generate_cid(aliases_content)
        create_cid_record(aliases_cid, aliases_content)

        # Create boot CID that references a missing CID
        missing_cid = generate_cid(b"missing")
        boot_payload = {
            'version': 6,
            'aliases': aliases_cid,
            'servers': missing_cid,  # This one is missing
        }
        boot_content = json.dumps(boot_payload).encode('utf-8')
        boot_cid = generate_cid(boot_content)
        create_cid_record(boot_cid, boot_content)

        success, error = verify_boot_cid_dependencies(boot_cid)
        assert not success, "Should fail when CID is missing"
        assert missing_cid in error, "Error should mention missing CID"
        print(f"   ✓ Correctly detected missing CID: {missing_cid[:20]}...")

        print("\n3. Testing successful import...")
        # Create server content
        servers_data = [{'name': 'test-server', 'definition': 'echo test'}]
        servers_content = json.dumps(servers_data).encode('utf-8')
        servers_cid = generate_cid(servers_content)
        create_cid_record(servers_cid, servers_content)

        # Create complete boot CID with all dependencies
        complete_payload = {
            'version': 6,
            'aliases': aliases_cid,
            'servers': servers_cid,
        }
        complete_content = json.dumps(complete_payload).encode('utf-8')
        complete_boot_cid = generate_cid(complete_content)
        create_cid_record(complete_boot_cid, complete_content)

        success, error = import_boot_cid(app, complete_boot_cid)
        assert success, f"Import should succeed: {error}"
        print("   ✓ Successfully imported boot CID")

        # Verify imports
        alias = Alias.query.filter_by(name='test-alias').first()
        assert alias is not None, "Alias should be imported"
        print(f"   ✓ Alias '{alias.name}' imported")

        server = Server.query.filter_by(name='test-server').first()
        assert server is not None, "Server should be imported"
        print(f"   ✓ Server '{server.name}' imported")

        print("\n4. Testing error messages...")
        # Test invalid CID
        success, error = import_boot_cid(app, "invalid-cid")
        assert not success, "Should fail with invalid CID"
        assert "Invalid CID format" in error, "Should mention invalid format"
        print("   ✓ Invalid CID error message is helpful")

        # Test missing CID
        nonexistent_cid = generate_cid(b"nonexistent")
        success, error = import_boot_cid(app, nonexistent_cid)
        assert not success, "Should fail with missing CID"
        assert "not found in database" in error, "Should mention CID not found"
        assert "cids directory" in error, "Should mention cids directory"
        print("   ✓ Missing CID error message is helpful")

        print("\n✅ All manual tests passed!")


if __name__ == '__main__':
    try:
        test_boot_cid_import()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
