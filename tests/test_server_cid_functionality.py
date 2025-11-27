#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from cid_core import is_literal_cid
from cid_utils import CID_LENGTH, CID_MIN_LENGTH, _base64url_encode, encode_cid_length, save_server_definition_as_cid
from db_access import get_cid_by_path
from models import CID, Server


def test_server_cid_functionality():
    """Test that server definitions are saved as CIDs when created/updated"""

    # Skip test if app is mocked (running with unittest discover)
    from unittest.mock import Mock
    if isinstance(app, Mock):
        print("Skipping test due to Flask-Login conflicts when running with unittest discover")
        return

    # Use in-memory SQLite for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        # Create tables
        db.drop_all()  # Clear any existing tables
        db.create_all()

        # Test 1: Test save_server_definition_as_cid function
        definition1 = "print('Hello World')"
        cid1 = save_server_definition_as_cid(definition1)

        # Verify CID was generated
        assert cid1 is not None
        expected_cid = encode_cid_length(len(definition1.encode('utf-8'))) + _base64url_encode(definition1.encode('utf-8'))
        assert cid1 == expected_cid
        assert CID_MIN_LENGTH <= len(cid1) <= CID_LENGTH
        print(f"✓ CID generated: {cid1}")

        # Verify CID resolves correctly (via DB for hash-based or literal extraction)
        cid_record = get_cid_by_path(f"/{cid1}")
        assert cid_record is not None
        assert cid_record.file_data == definition1.encode('utf-8')
        print("✓ CID resolves correctly")

        # Test 2: Test duplicate CID handling
        cid2 = save_server_definition_as_cid(definition1)
        assert cid1 == cid2  # Should return same CID for same content

        # For literal CIDs, no DB record should exist; for hash-based, only one
        if not is_literal_cid(cid1):
            cid_count = CID.query.filter_by(path=f"/{cid1}").count()
            assert cid_count == 1
        print("✓ Duplicate CID handling works correctly")

        # Test 3: Test different content generates different CID
        definition2 = "print('Hello Universe')"
        cid3 = save_server_definition_as_cid(definition2)
        assert cid3 != cid1
        print(f"✓ Different content generates different CID: {cid3}")

        # Test 4: Test direct server creation with CID
        definition = "print('Server code')"
        cid = save_server_definition_as_cid(definition)

        # Create server directly
        server = Server(
            name="test_server",
            definition=definition,
            definition_cid=cid,
        )
        db.session.add(server)
        db.session.commit()

        # Verify server was created with CID
        assert server.definition == "print('Server code')"
        assert server.definition_cid is not None
        expected_definition_cid = encode_cid_length(len(definition.encode('utf-8'))) + _base64url_encode(definition.encode('utf-8'))
        assert server.definition_cid == expected_definition_cid
        assert CID_MIN_LENGTH <= len(server.definition_cid) <= CID_LENGTH
        print(f"✓ Server created with CID: {server.definition_cid}")

        # Verify CID resolves correctly for server definition
        server_cid_record = get_cid_by_path(f"/{server.definition_cid}")
        assert server_cid_record is not None
        print("✓ Server definition CID resolves correctly")

        # Test 5: Test server update with CID
        original_cid = server.definition_cid
        new_definition = "print('Updated server code')"

        # Update server with new definition and CID
        if new_definition != server.definition:
            new_cid = save_server_definition_as_cid(new_definition)
            server.definition_cid = new_cid

        server.definition = new_definition
        db.session.commit()

        # Verify server was updated with new CID
        db.session.refresh(server)
        assert server.definition_cid is not None
        assert server.definition_cid != original_cid  # Should be different CID
        print(f"✓ Server updated with new CID: {server.definition_cid}")

        # Verify new CID resolves correctly
        updated_cid_record = get_cid_by_path(f"/{server.definition_cid}")
        assert updated_cid_record is not None
        assert updated_cid_record.file_data == "print('Updated server code')".encode('utf-8')
        print("✓ Updated server definition CID resolves correctly")

        # Test 6: Test server update with same definition (should keep same CID)
        current_cid = server.definition_cid
        same_definition = "print('Updated server code')"

        # Should not generate new CID since definition is the same
        if same_definition == server.definition:
            # No CID update needed
            pass
        else:
            new_cid = save_server_definition_as_cid(same_definition)
            server.definition_cid = new_cid

        server.definition = same_definition
        db.session.commit()

        # CID should remain the same since definition didn't change
        db.session.refresh(server)
        assert server.definition_cid == current_cid
        print("✓ Server update with same definition keeps same CID")

        print("\n🎉 All server CID functionality tests passed!")
        # Remove return statement - test functions should not return values

if __name__ == '__main__':
    try:
        test_server_cid_functionality()
        print("✅ Server CID functionality test completed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
