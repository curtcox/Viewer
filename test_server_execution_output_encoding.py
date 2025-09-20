import sys
import types
import unittest

# Lightweight module mocks so importing server_execution doesn't require external deps
mock_flask = types.ModuleType("flask")
mock_flask.jsonify = lambda *a, **k: None
mock_flask.make_response = lambda x: types.SimpleNamespace(headers={}, status_code=200, data=x)
mock_flask.redirect = lambda url: ("redirect", url)
mock_flask.render_template = lambda *a, **k: ""
mock_flask.request = types.SimpleNamespace(
    path="/", query_string=b"", remote_addr="127.0.0.1", user_agent=types.SimpleNamespace(string="UA"),
    headers={}, form={}, args={}, endpoint="ep", scheme="http", host="localhost", method="GET",
)
sys.modules.setdefault("flask", mock_flask)

mock_flask_login = types.ModuleType("flask_login")
mock_flask_login.current_user = types.SimpleNamespace(is_authenticated=False, id=None)
sys.modules.setdefault("flask_login", mock_flask_login)

# Other internal modules referenced but not needed for these tests
mock_cid_utils = types.ModuleType("cid_utils")
mock_cid_utils.generate_cid = lambda b: "deadbeef"
mock_cid_utils.get_current_secret_definitions_cid = lambda *a, **k: "cid_s"
mock_cid_utils.get_current_server_definitions_cid = lambda *a, **k: "cid_srv"
mock_cid_utils.get_current_variable_definitions_cid = lambda *a, **k: "cid_v"
mock_cid_utils.get_extension_from_mime_type = lambda ct: "html" if ct == "text/html" else ""
sys.modules.setdefault("cid_utils", mock_cid_utils)

mock_db_access = types.ModuleType("db_access")
mock_db_access.create_cid_record = lambda *a, **k: None
mock_db_access.create_server_invocation = lambda *a, **k: types.SimpleNamespace(invoked_at=None, invocation_cid=None)
mock_db_access.get_cid_by_path = lambda *a, **k: None
mock_db_access.get_server_by_name = lambda *a, **k: None
mock_db_access.get_user_secrets = lambda *a, **k: []
mock_db_access.get_user_servers = lambda *a, **k: []
mock_db_access.get_user_variables = lambda *a, **k: []
mock_db_access.save_entity = lambda *a, **k: None
sys.modules.setdefault("db_access", mock_db_access)

mock_runner = types.ModuleType("text_function_runner")
mock_runner.run_text_function = lambda code, args: {"output": "", "content_type": "text/html"}
sys.modules.setdefault("text_function_runner", mock_runner)

# Import the function under test after setting up mocks
from server_execution import _encode_output


class TestServerExecutionOutputEncoding(unittest.TestCase):
    def test_encode_bytes_passthrough(self):
        data = b"hello"
        self.assertEqual(_encode_output(data), data)

    def test_encode_str_to_utf8(self):
        s = "hello"
        self.assertEqual(_encode_output(s), b"hello")

    def test_encode_list_of_ints_to_bytes(self):
        data = [104, 101, 108, 108, 111]  # 'hello'
        self.assertEqual(_encode_output(data), b"hello")

    def test_encode_list_of_strings_join_then_utf8(self):
        # This represents a realistic server output where pieces of text are built as a list
        parts = ["hello", " ", "world"]
        # Expected desired behavior: join strings then encode as UTF-8
        expected = b"hello world"
        # This currently raises TypeError: 'str' object cannot be interpreted as an integer
        # Reproduces the bug in _encode_output
        self.assertEqual(_encode_output(parts), expected)


if __name__ == "__main__":
    unittest.main()
