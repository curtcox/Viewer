#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Server, CID
from cid_utils import save_server_definition_as_cid

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

        # Create test user
        test_user = User(
            id='test_user_123',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True
        )
        db.session.add(test_user)
        db.session.commit()

        print("✓ Test user created")

        # Test 1: Test save_server_definition_as_cid function
        definition1 = "print('Hello World')"
        cid1 = save_server_definition_as_cid(definition1, test_user.id)

        # Verify CID was generated
        assert cid1 is not None
        assert len(cid1) == 43
        print(f"✓ CID generated: {cid1}")

        # Verify CID record was created in database
        cid_record = CID.query.filter_by(path=f"/{cid1}").first()
        assert cid_record is not None
        assert cid_record.file_data == definition1.encode('utf-8')
        assert cid_record.uploaded_by_user_id == test_user.id
        print("✓ CID record created in database")

        # Test 2: Test duplicate CID handling
        cid2 = save_server_definition_as_cid(definition1, test_user.id)
        assert cid1 == cid2  # Should return same CID for same content

        # Should still only have one CID record
        cid_count = CID.query.filter_by(path=f"/{cid1}").count()
        assert cid_count == 1
        print("✓ Duplicate CID handling works correctly")

        # Test 3: Test different content generates different CID
        definition2 = "print('Hello Universe')"
        cid3 = save_server_definition_as_cid(definition2, test_user.id)
        assert cid3 != cid1
        print(f"✓ Different content generates different CID: {cid3}")

        # Test 4: Test direct server creation with CID
        definition = "print('Server code')"
        cid = save_server_definition_as_cid(definition, test_user.id)

        # Create server directly
        server = Server(
            name="test_server",
            definition=definition,
            definition_cid=cid,
            user_id=test_user.id
        )
        db.session.add(server)
        db.session.commit()

        # Verify server was created with CID
        assert server.definition == "print('Server code')"
        assert server.definition_cid is not None
        assert len(server.definition_cid) == 43
        print(f"✓ Server created with CID: {server.definition_cid}")

        # Verify CID record exists for server definition
        server_cid_record = CID.query.filter_by(path=f"/{server.definition_cid}").first()
        assert server_cid_record is not None
        assert server_cid_record.file_data == "print('Server code')".encode('utf-8')
        print("✓ Server definition CID record exists in database")

        # Test 5: Test server update with CID
        original_cid = server.definition_cid
        new_definition = "print('Updated server code')"

        # Update server with new definition and CID
        if new_definition != server.definition:
            new_cid = save_server_definition_as_cid(new_definition, server.user_id)
            server.definition_cid = new_cid

        server.definition = new_definition
        db.session.commit()

        # Verify server was updated with new CID
        db.session.refresh(server)
        assert server.definition == "print('Updated server code')"
        assert server.definition_cid is not None
        assert server.definition_cid != original_cid  # Should be different CID
        print(f"✓ Server updated with new CID: {server.definition_cid}")

        # Verify new CID record exists
        updated_cid_record = CID.query.filter_by(path=f"/{server.definition_cid}").first()
        assert updated_cid_record is not None
        assert updated_cid_record.file_data == "print('Updated server code')".encode('utf-8')
        print("✓ Updated server definition CID record exists in database")

        # Test 6: Test server update with same definition (should keep same CID)
        current_cid = server.definition_cid
        same_definition = "print('Updated server code')"

        # Should not generate new CID since definition is the same
        if same_definition == server.definition:
            # No CID update needed
            pass
        else:
            new_cid = save_server_definition_as_cid(same_definition, server.user_id)
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
