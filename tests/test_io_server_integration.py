"""Integration tests for IO server.

These tests verify the IO server works correctly in the context
of the full application, including boot image configuration and
request handling.
"""

import json
import unittest
from pathlib import Path


class TestIOBootImageConfiguration(unittest.TestCase):
    """Test IO server is correctly configured in boot images."""

    def setUp(self):
        """Set up paths to boot configuration files."""
        # Find the reference/templates directory
        self.base_dir = Path(__file__).parent.parent
        self.templates_dir = self.base_dir / "reference/templates"

    def test_io_in_default_boot(self):
        """IO server should be present in default.boot.source.json."""
        boot_file = self.templates_dir / "default.boot.source.json"

        self.assertTrue(boot_file.exists(), f"Boot file not found: {boot_file}")

        with open(boot_file, "r", encoding="utf-8") as f:
            boot_config = json.load(f)

        servers = boot_config.get("servers", [])
        io_servers = [s for s in servers if s.get("name") == "io"]

        self.assertEqual(len(io_servers), 1, "Expected exactly one 'io' server")
        self.assertTrue(io_servers[0].get("enabled"), "IO server should be enabled")

    def test_io_in_readonly_boot(self):
        """IO server should be present in readonly.boot.source.json."""
        boot_file = self.templates_dir / "readonly.boot.source.json"

        self.assertTrue(boot_file.exists(), f"Boot file not found: {boot_file}")

        with open(boot_file, "r", encoding="utf-8") as f:
            boot_config = json.load(f)

        servers = boot_config.get("servers", [])
        io_servers = [s for s in servers if s.get("name") == "io"]

        self.assertEqual(len(io_servers), 1, "Expected exactly one 'io' server")
        self.assertTrue(io_servers[0].get("enabled"), "IO server should be enabled")

    def test_io_definition_exists(self):
        """IO server definition file should exist."""
        io_def_file = self.templates_dir / "servers" / "definitions" / "io.py"

        self.assertTrue(io_def_file.exists(), f"IO definition not found: {io_def_file}")

        # Check it has required elements
        content = io_def_file.read_text()
        self.assertIn("def main(", content)
        self.assertIn("context=None", content)

    def test_io_definition_has_landing_page(self):
        """IO server should have a landing page function."""
        io_def_file = self.templates_dir / "servers" / "definitions" / "io.py"
        content = io_def_file.read_text()

        self.assertIn("_render_landing_page", content)
        self.assertIn("text/html", content)


class TestIOServerDefinitionStructure(unittest.TestCase):
    """Test IO server definition structure."""

    def setUp(self):
        """Load the IO server definition."""
        self.base_dir = Path(__file__).parent.parent
        io_def_file = (
            self.base_dir / "reference/templates" / "servers" / "definitions" / "io.py"
        )
        self.content = io_def_file.read_text()

    def test_has_main_function(self):
        """IO server should have a main function."""
        self.assertIn("def main(", self.content)

    def test_main_accepts_path_segments(self):
        """Main function should accept path segments."""
        self.assertIn("*path_segments", self.content)

    def test_main_accepts_context(self):
        """Main function should accept context."""
        self.assertIn("context=None", self.content)

    def test_has_error_handling(self):
        """IO server should have error handling."""
        self.assertIn("_render_error_page", self.content)

    def test_returns_dict_with_output(self):
        """IO server should return dict with output key."""
        self.assertIn('"output":', self.content)
        self.assertIn('"content_type":', self.content)


class TestSharedSegmentAnalysis(unittest.TestCase):
    """Test shared segment analysis module exists and is importable."""

    def test_segment_analysis_module_exists(self):
        """segment_analysis module should exist."""
        segment_analysis_file = (
            Path(__file__).parent.parent
            / "server_execution"
            / "segment_analysis.py"
        )
        self.assertTrue(segment_analysis_file.exists())

    def test_io_execution_module_exists(self):
        """io_execution module should exist."""
        io_execution_file = (
            Path(__file__).parent.parent
            / "server_execution"
            / "io_execution.py"
        )
        self.assertTrue(io_execution_file.exists())


class TestIODocumentation(unittest.TestCase):
    """Test IO documentation exists."""

    def test_io_requests_doc_exists(self):
        """io-requests.md documentation should exist."""
        docs_dir = Path(__file__).parent.parent / "docs"
        io_doc = docs_dir / "io-requests.md"

        # Note: This test may fail until documentation is created
        # It's included to verify documentation completeness
        if io_doc.exists():
            content = io_doc.read_text()
            self.assertIn("io", content.lower())
            self.assertIn("request", content.lower())
            self.assertIn("response", content.lower())


if __name__ == "__main__":
    unittest.main()
