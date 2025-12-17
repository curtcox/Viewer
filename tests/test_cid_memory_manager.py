# tests/test_cid_memory_manager.py
"""Tests for CID memory management in read-only mode."""

import pytest

from app import create_app
from cid import CID
from cid_memory_manager import CIDMemoryManager
from db_config import DatabaseConfig, DatabaseMode
from readonly_config import ReadOnlyConfig


class TestCIDMemoryManager:
    """Tests for CIDMemoryManager."""

    def setup_method(self):
        """Reset config before each test."""
        ReadOnlyConfig.reset()
        DatabaseConfig.reset()

    def teardown_method(self):
        """Reset config after each test."""
        ReadOnlyConfig.reset()
        DatabaseConfig.reset()

    def test_check_cid_size_normal_mode(self):
        """CID size check should pass in normal mode."""
        # Don't enable read-only mode
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            # Should not raise even for large content
            large_content = b"x" * (2 * 1024 * 1024 * 1024)  # 2GB
            CIDMemoryManager.check_cid_size(len(large_content))

    def test_check_cid_size_within_limit(self):
        """CID size check should pass for content within limit."""
        ReadOnlyConfig.set_read_only_mode(True)
        ReadOnlyConfig.set_max_cid_memory(10 * 1024 * 1024)  # 10MB
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            # Should not raise for content within limit
            content = b"x" * (5 * 1024 * 1024)  # 5MB
            CIDMemoryManager.check_cid_size(len(content))

    def test_check_cid_size_exceeds_limit(self):
        """CID size check should abort for oversized content."""
        ReadOnlyConfig.set_read_only_mode(True)
        ReadOnlyConfig.set_max_cid_memory(10 * 1024 * 1024)  # 10MB
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            from werkzeug.exceptions import RequestEntityTooLarge
            
            # Should raise 413 for content exceeding limit
            with pytest.raises(RequestEntityTooLarge):
                large_content = b"x" * (20 * 1024 * 1024)  # 20MB
                CIDMemoryManager.check_cid_size(len(large_content))

    def test_get_total_cid_size_empty(self):
        """Total CID size should be 0 for empty database."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            total_size = CIDMemoryManager.get_total_cid_size()
            assert total_size == 0

    def test_get_total_cid_size_with_cids(self):
        """Total CID size should sum all CID sizes."""
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            from db_access.cids import create_cid_record
            
            # Create some CIDs with valid CID values
            cid1 = CID.from_bytes(b"content1").value
            cid2 = CID.from_bytes(b"content22").value
            create_cid_record(cid1, b"content1")  # 8 bytes
            create_cid_record(cid2, b"content22")  # 9 bytes
            
            total_size = CIDMemoryManager.get_total_cid_size()
            assert total_size == 17  # 8 + 9

    def test_ensure_memory_available_with_space(self):
        """Should not evict when enough space available."""
        ReadOnlyConfig.set_read_only_mode(True)
        ReadOnlyConfig.set_max_cid_memory(1024)  # 1KB
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            from db_access.cids import create_cid_record
            from models import CID as CIDModel
            
            # Create a small CID with valid CID value
            cid_value = CID.from_bytes(b"small").value
            create_cid_record(cid_value, b"small")  # 5 bytes
            
            # Request space for another small CID
            CIDMemoryManager.ensure_memory_available(5)
            
            # Original CID should still exist
            assert CIDModel.query.count() == 1

    def test_ensure_memory_available_evicts_largest(self):
        """Should evict largest CIDs when memory needed."""
        ReadOnlyConfig.set_read_only_mode(True)
        ReadOnlyConfig.set_max_cid_memory(100)  # 100 bytes
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        
        app = create_app({"TESTING": True})
        
        with app.app_context():
            from db_access.cids import create_cid_record
            from models import CID as CIDModel
            
            # Fill up memory with CIDs of different sizes
            content1 = b"x" * 10
            content2 = b"x" * 40
            content3 = b"x" * 20
            
            cid1 = CID.from_bytes(content1).value
            cid2 = CID.from_bytes(content2).value  # largest
            cid3 = CID.from_bytes(content3).value
            
            create_cid_record(cid1, content1)   # 10 bytes
            create_cid_record(cid2, content2)   # 40 bytes (largest)
            create_cid_record(cid3, content3)   # 20 bytes
            
            # Total: 70 bytes, available: 30 bytes
            # Request 50 bytes - should evict the 40-byte CID
            CIDMemoryManager.ensure_memory_available(50)
            
            # Should have 2 CIDs left
            assert CIDModel.query.count() == 2
            
            # The 40-byte CID (cid2) should be gone
            assert CIDModel.query.filter_by(path=f"/{cid2}").first() is None
            
            # The other two should still exist
            assert CIDModel.query.filter_by(path=f"/{cid1}").first() is not None
            assert CIDModel.query.filter_by(path=f"/{cid3}").first() is not None
