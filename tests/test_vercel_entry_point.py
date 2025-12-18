"""Tests for api/index.py Vercel entry point."""
import os
import sys
from pathlib import Path


class TestVercelEntryPoint:
    """Test suite for Vercel serverless function entry point."""

    def test_read_only_mode_enabled_from_env(self):
        """Test that READ_ONLY environment variable enables both read-only mode and sets database to memory mode."""
        # Store original state
        original_read_only = os.environ.get("READ_ONLY")
        original_testing = os.environ.get("TESTING")
        
        try:
            # Set environment variables
            os.environ["READ_ONLY"] = "true"
            os.environ["TESTING"] = "1"
            
            # Import fresh to pick up environment changes
            if "api.index" in sys.modules:
                del sys.modules["api.index"]
            if "app" in sys.modules:
                del sys.modules["app"]
            
            # Add api directory to path if not already there
            api_dir = str(Path(__file__).parent.parent / "api")
            if api_dir not in sys.path:
                sys.path.insert(0, api_dir)
            
            # Import and check read-only mode
            from readonly_config import ReadOnlyConfig
            from db_config import DatabaseConfig, DatabaseMode
            ReadOnlyConfig.reset()  # Reset first
            DatabaseConfig.reset()  # Reset database config too
            
            # Now import the api module which should enable read-only mode
            import index  # noqa: F401 - Import has side effect of enabling read-only mode
            
            # Verify read-only mode is enabled
            assert ReadOnlyConfig.is_read_only_mode() is True
            # Verify database mode is set to memory
            assert DatabaseConfig.get_mode() == DatabaseMode.MEMORY
            
        finally:
            # Restore original environment
            if original_read_only is not None:
                os.environ["READ_ONLY"] = original_read_only
            elif "READ_ONLY" in os.environ:
                del os.environ["READ_ONLY"]
            
            if original_testing is not None:
                os.environ["TESTING"] = original_testing
            elif "TESTING" in os.environ:
                del os.environ["TESTING"]
            
            # Clean up imports
            if "api.index" in sys.modules:
                del sys.modules["api.index"]
            if "index" in sys.modules:
                del sys.modules["index"]
            
            # Reset read-only config and database config
            from readonly_config import ReadOnlyConfig
            from db_config import DatabaseConfig
            ReadOnlyConfig.reset()
            DatabaseConfig.reset()

    def test_read_only_mode_not_enabled_when_env_false(self):
        """Test that READ_ONLY=false does not enable read-only mode."""
        # Store original state
        original_read_only = os.environ.get("READ_ONLY")
        original_testing = os.environ.get("TESTING")
        
        try:
            # Set environment variables
            os.environ["READ_ONLY"] = "false"
            os.environ["TESTING"] = "1"
            
            # Clean up modules
            if "api.index" in sys.modules:
                del sys.modules["api.index"]
            if "app" in sys.modules:
                del sys.modules["app"]
            
            from readonly_config import ReadOnlyConfig
            from db_config import DatabaseConfig, DatabaseMode
            ReadOnlyConfig.reset()
            DatabaseConfig.reset()
            
            # Import the api module
            import index  # noqa: F401 - Import has side effect on read-only mode
            
            # Verify read-only mode is NOT enabled
            assert ReadOnlyConfig.is_read_only_mode() is False
            # Verify database mode is NOT memory (should be default DISK)
            assert DatabaseConfig.get_mode() == DatabaseMode.DISK
            
        finally:
            # Restore original environment
            if original_read_only is not None:
                os.environ["READ_ONLY"] = original_read_only
            elif "READ_ONLY" in os.environ:
                del os.environ["READ_ONLY"]
            
            if original_testing is not None:
                os.environ["TESTING"] = original_testing
            elif "TESTING" in os.environ:
                del os.environ["TESTING"]
            
            # Clean up imports
            if "api.index" in sys.modules:
                del sys.modules["api.index"]
            if "index" in sys.modules:
                del sys.modules["index"]
            
            from readonly_config import ReadOnlyConfig
            from db_config import DatabaseConfig
            ReadOnlyConfig.reset()
            DatabaseConfig.reset()

    def test_read_only_mode_respects_various_true_values(self):
        """Test that various true values enable read-only mode."""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]
        
        original_read_only = os.environ.get("READ_ONLY")
        original_testing = os.environ.get("TESTING")
        
        for value in true_values:
            try:
                os.environ["READ_ONLY"] = value
                os.environ["TESTING"] = "1"
                
                # Clean up modules
                if "api.index" in sys.modules:
                    del sys.modules["api.index"]
                if "index" in sys.modules:
                    del sys.modules["index"]
                if "app" in sys.modules:
                    del sys.modules["app"]
                
                from readonly_config import ReadOnlyConfig
                from db_config import DatabaseConfig, DatabaseMode
                ReadOnlyConfig.reset()
                DatabaseConfig.reset()
                
                # Import the api module
                import index  # noqa: F401 - Import has side effect of enabling read-only mode
                
                # Verify read-only mode is enabled
                assert ReadOnlyConfig.is_read_only_mode() is True, f"Failed for value: {value}"
                # Verify database mode is set to memory
                assert DatabaseConfig.get_mode() == DatabaseMode.MEMORY, f"Failed for value: {value}"
                
            finally:
                # Clean up for next iteration
                if "api.index" in sys.modules:
                    del sys.modules["api.index"]
                if "index" in sys.modules:
                    del sys.modules["index"]
                if "app" in sys.modules:
                    del sys.modules["app"]
        
        # Final cleanup
        if original_read_only is not None:
            os.environ["READ_ONLY"] = original_read_only
        elif "READ_ONLY" in os.environ:
            del os.environ["READ_ONLY"]
        
        if original_testing is not None:
            os.environ["TESTING"] = original_testing
        elif "TESTING" in os.environ:
            del os.environ["TESTING"]
        
        from readonly_config import ReadOnlyConfig
        from db_config import DatabaseConfig
        ReadOnlyConfig.reset()
        DatabaseConfig.reset()
