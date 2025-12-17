# tests/integration/test_readonly_mode.py
"""Integration tests for read-only mode functionality."""

import pytest

from app import create_app
from db_config import DatabaseConfig, DatabaseMode
from readonly_config import ReadOnlyConfig


class TestReadOnlyModeIntegration:
    """Integration tests for read-only mode."""

    def setup_method(self):
        """Reset config before each test."""
        ReadOnlyConfig.reset()
        DatabaseConfig.reset()

    def teardown_method(self):
        """Reset config after each test."""
        ReadOnlyConfig.reset()
        DatabaseConfig.reset()

    def test_read_only_mode_blocks_post_requests(self):
        """POST requests should return 405 in read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        client = app.test_client()
        
        # Try to create a server (POST request)
        response = client.post("/servers/new", data={
            "name": "test_server",
            "definition": "def main(): pass"
        })
        
        assert response.status_code == 405
        assert b"not allowed in read-only mode" in response.data.lower()

    def test_read_only_mode_blocks_delete_requests(self):
        """DELETE requests should return 405 in read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        client = app.test_client()
        
        # Try to delete a server
        response = client.delete("/servers/test/delete")
        
        assert response.status_code == 405

    def test_read_only_mode_allows_get_requests(self):
        """GET requests should work in read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        client = app.test_client()
        
        # GET requests should work
        response = client.get("/servers")
        
        # Should be successful (200) or redirect (302/303)
        assert response.status_code in (200, 302, 303)

    def test_normal_mode_allows_state_changes(self):
        """State changes should work in normal mode."""
        # Don't enable read-only mode
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        client = app.test_client()
        
        # POST should work (though may fail for other reasons like validation)
        response = client.post("/servers/new", data={
            "name": "test_server",
            "definition": "def main(): pass"
        })
        
        # Should not be 405
        assert response.status_code != 405

    def test_page_views_not_tracked_in_readonly_mode(self):
        """Page views should not be tracked in read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        client = app.test_client()
        
        # Make a request that would normally be tracked
        client.get("/")
        
        # Check that no page views were recorded
        with app.app_context():
            from models import PageView
            page_views = PageView.query.count()
            assert page_views == 0

    def test_interactions_not_recorded_in_readonly_mode(self):
        """Entity interactions should not be recorded in read-only mode."""
        ReadOnlyConfig.set_read_only_mode(True)
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            from db_access.interactions import record_entity_interaction, EntityInteractionRequest
            from datetime import datetime, timezone
            
            # Try to record an interaction
            request = EntityInteractionRequest(
                entity_type="server",
                entity_name="test",
                action="save",
                message="test message",
                content="test content",
                created_at=datetime.now(timezone.utc)
            )
            
            result = record_entity_interaction(request)
            
            # Should return None in read-only mode
            assert result is None
