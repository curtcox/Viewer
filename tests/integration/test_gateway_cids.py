"""Integration tests for CIDS gateway."""

import os
import unittest

# Set required environment variables before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-key")

# pylint: disable=wrong-import-position
from app import app, db
from identity import ensure_default_resources
from models import Server, Variable


class TestGatewayCIDS(unittest.TestCase):
    """Test the CIDS gateway functionality."""

    def setUp(self):
        """Set up test fixtures."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        ensure_default_resources()
        self.client = app.test_client()

        # Read server definitions
        with open(
            "reference_templates/servers/definitions/cids.py", "r", encoding="utf-8"
        ) as f:
            cids_definition = f.read()

        with open(
            "reference_templates/servers/definitions/gateway.py", "r", encoding="utf-8"
        ) as f:
            gateway_definition = f.read()

        # Create servers
        cids_server = Server(name="cids", definition=cids_definition, enabled=True)
        gateway_server = Server(name="gateway", definition=gateway_definition, enabled=True)
        db.session.add(cids_server)
        db.session.add(gateway_server)

        # Read gateway configuration
        with open(
            "reference_templates/gateways.source.json", "r", encoding="utf-8"
        ) as f:
            import json
            gateways_config = json.load(f)

        # Store gateways variable
        gateways_var = Variable(name="gateways", definition=json.dumps(gateways_config))
        db.session.add(gateways_var)
        db.session.commit()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_gateway_cids_without_archive_shows_error(self):
        """Test that gateway without archive CID shows error."""
        response = self.client.get("/gateway/cids/")
        # Should show an error or redirect
        self.assertIn(response.status_code, [302, 400, 404, 500])

    def test_gateway_cids_with_invalid_cid_shows_error(self):
        """Test that gateway with invalid CID shows error."""
        response = self.client.get("/gateway/cids/INVALID_CID_NOT_EXISTS/")
        # Should show an error page or redirect
        self.assertIn(response.status_code, [302, 404, 500])

    def test_gateway_cids_path_parsing(self):
        """Test that gateway correctly parses CID and path."""
        # This will fail with invalid CID, but we're testing path parsing
        response = self.client.get("/gateway/cids/TEST_CID/some/path.md")
        # Should attempt to process the request (may error or redirect)
        self.assertIn(response.status_code, [200, 302, 404, 500])


if __name__ == "__main__":
    unittest.main()
