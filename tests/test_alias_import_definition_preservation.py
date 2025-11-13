"""Unit tests for alias import definition preservation."""
import unittest

from routes.import_export.import_entities import prepare_alias_import


class TestAliasImportDefinitionPreservation(unittest.TestCase):
    """Test that alias import preserves the original definition patterns."""

    def test_prepare_alias_import_preserves_literal_pattern(self):
        """Test that literal pattern in definition is preserved during import."""
        entry = {
            'name': 'cli-test-alias',
            'definition': '/cli-test -> /cli-target',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'cli-test-alias')
        self.assertEqual(result.definition, '/cli-test -> /cli-target')
        self.assertEqual(len(errors), 0)

    def test_prepare_alias_import_preserves_literal_pattern_with_options(self):
        """Test that literal pattern with options is preserved during import."""
        entry = {
            'name': 'test-alias-2',
            'definition': '/pattern -> /target [ignore-case]',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'test-alias-2')
        self.assertEqual(result.definition, '/pattern -> /target [ignore-case]')
        # The ignore-case option is preserved in the definition string itself
        self.assertIn('[ignore-case]', result.definition)
        self.assertEqual(len(errors), 0)

    def test_prepare_alias_import_preserves_regex_pattern(self):
        """Test that regex pattern is preserved during import."""
        entry = {
            'name': 'regex-alias',
            'definition': r'/api/.* -> /backend [regex]',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'regex-alias')
        self.assertEqual(result.definition, r'/api/.* -> /backend [regex]')
        self.assertEqual(len(errors), 0)

    def test_prepare_alias_import_preserves_glob_pattern(self):
        """Test that glob pattern is preserved during import."""
        entry = {
            'name': 'glob-alias',
            'definition': '/files/*.txt -> /text-files [glob]',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'glob-alias')
        self.assertEqual(result.definition, '/files/*.txt -> /text-files [glob]')
        self.assertEqual(len(errors), 0)

    def test_prepare_alias_import_preserves_root_pattern(self):
        """Test that root pattern / is preserved during import."""
        entry = {
            'name': 'root-alias',
            'definition': '/ -> /home',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'root-alias')
        self.assertEqual(result.definition, '/ -> /home')
        self.assertEqual(len(errors), 0)

    def test_prepare_alias_import_different_name_and_pattern(self):
        """Test import when alias name differs from pattern."""
        entry = {
            'name': 'my-alias',
            'definition': '/some-path -> /target',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'my-alias')
        # The definition should preserve the original pattern, not change it to the alias name
        self.assertEqual(result.definition, '/some-path -> /target')
        self.assertEqual(len(errors), 0)

    def test_prepare_alias_import_multiline_definition(self):
        """Test import with multiline definition preserves primary line."""
        entry = {
            'name': 'multi-alias',
            'definition': '/primary -> /target\n  /sub -> /sub-target',
        }
        reserved_routes = set()
        cid_map = {}
        errors = []

        result = prepare_alias_import(entry, reserved_routes, cid_map, errors)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'multi-alias')
        # The primary line should be preserved
        self.assertIn('/primary -> /target', result.definition)
        self.assertIn('/sub -> /sub-target', result.definition)
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
