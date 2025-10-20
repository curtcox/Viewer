import unittest

from app import create_app
from routes.aliases import _describe_target_path


class AliasDefinitionTargetRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({'TESTING': True})
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.request_ctx = self.app.test_request_context()
        self.request_ctx.push()

    def tearDown(self) -> None:
        self.request_ctx.pop()
        self.app_ctx.pop()

    def test_describe_target_path_handles_cids(self):
        result = _describe_target_path('/ABC12345')
        self.assertIsNotNone(result)
        self.assertEqual(result.get('kind'), 'cid')
        self.assertEqual(result.get('cid'), 'ABC12345')
        self.assertFalse(result.get('suffix'))

    def test_describe_target_path_handles_cids_with_prefix(self):
        result = _describe_target_path('/CID/ABC12345.txt?download=1')
        self.assertIsNotNone(result)
        self.assertEqual(result.get('kind'), 'cid')
        self.assertEqual(result.get('cid'), 'ABC12345')
        self.assertEqual(result.get('suffix'), '?download=1')

    def test_describe_target_path_handles_servers(self):
        result = _describe_target_path('/servers/example')
        self.assertIsNotNone(result)
        self.assertEqual(result.get('kind'), 'server')
        self.assertEqual(result.get('name'), 'example')
        self.assertEqual(result.get('url'), '/servers/example')

    def test_describe_target_path_handles_aliases(self):
        result = _describe_target_path('/aliases/docs')
        self.assertIsNotNone(result)
        self.assertEqual(result.get('kind'), 'alias')
        self.assertEqual(result.get('name'), 'docs')
        self.assertEqual(result.get('url'), '/aliases/docs')

    def test_describe_target_path_handles_generic_paths(self):
        result = _describe_target_path('/docs/latest')
        self.assertIsNotNone(result)
        self.assertEqual(result.get('kind'), 'path')
        self.assertEqual(result.get('display'), '/docs/latest')


if __name__ == '__main__':  # pragma: no cover - convenience for direct execution
    unittest.main()
