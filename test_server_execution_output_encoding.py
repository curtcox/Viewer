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

mock_identity = types.ModuleType("identity")
mock_identity.current_user = types.SimpleNamespace(id=None)
mock_identity.ensure_default_user = lambda: None
sys.modules.setdefault("identity", mock_identity)

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

# Import the module under test after setting up mocks
import server_execution  # noqa: E402


class TestServerExecutionOutputEncoding(unittest.TestCase):
    def test_encode_bytes_passthrough(self):
        data = b"hello"
        self.assertEqual(server_execution._encode_output(data), data)

    def test_encode_str_to_utf8(self):
        s = "hello"
        self.assertEqual(server_execution._encode_output(s), b"hello")

    def test_encode_list_of_ints_to_bytes(self):
        data = [104, 101, 108, 108, 111]  # 'hello'
        self.assertEqual(server_execution._encode_output(data), b"hello")

    def test_encode_list_of_strings_join_then_utf8(self):
        # This represents a realistic server output where pieces of text are built as a list
        parts = ["hello", " ", "world"]
        # Expected desired behavior: join strings then encode as UTF-8
        expected = b"hello world"
        # This currently raises TypeError: 'str' object cannot be interpreted as an integer
        # Reproduces the bug in _encode_output
        self.assertEqual(server_execution._encode_output(parts), expected)


class TestExecuteServerCodeSharedFlow(unittest.TestCase):
    def setUp(self):
        self.original_run_text_function = server_execution.run_text_function
        self.original_build_request_args = server_execution.build_request_args
        self.original_create_invocation = server_execution.create_server_invocation_record
        self.original_make_response = server_execution.make_response
        self.original_redirect = server_execution.redirect
        self.original_create_cid_record = server_execution.create_cid_record
        self.original_get_cid_by_path = server_execution.get_cid_by_path
        self.original_generate_cid = server_execution.generate_cid
        self.original_get_extension = server_execution.get_extension_from_mime_type
        self.original_current_user = server_execution.current_user
        self.original_render_error_html = server_execution._render_execution_error_html
        server_execution.current_user = types.SimpleNamespace(id="user-123")
        server_execution.build_request_args = lambda: {
            "request": {"path": "/mock"},
            "context": {"variables": {}, "secrets": {}, "servers": {}},
        }
        server_execution.create_server_invocation_record = lambda *a, **k: None
        server_execution.create_cid_record = lambda *a, **k: None
        server_execution.get_cid_by_path = lambda *a, **k: None
        server_execution.generate_cid = lambda b: "deadbeef"
        server_execution.get_extension_from_mime_type = (
            lambda ct: "html" if ct == "text/html" else ""
        )
        server_execution.make_response = lambda text: types.SimpleNamespace(
            headers={}, status_code=200, data=text
        )
        server_execution.redirect = lambda url: ("redirect", url)
        server_execution._render_execution_error_html = (
            lambda exc, code, args, server_name: "<html>Error</html>"
        )

    def tearDown(self):
        server_execution.run_text_function = self.original_run_text_function
        server_execution.build_request_args = self.original_build_request_args
        server_execution.create_server_invocation_record = self.original_create_invocation
        server_execution.make_response = self.original_make_response
        server_execution.redirect = self.original_redirect
        server_execution.create_cid_record = self.original_create_cid_record
        server_execution.get_cid_by_path = self.original_get_cid_by_path
        server_execution.generate_cid = self.original_generate_cid
        server_execution.get_extension_from_mime_type = self.original_get_extension
        server_execution.current_user = self.original_current_user
        server_execution._render_execution_error_html = (
            self.original_render_error_html
        )

    def test_execute_functions_share_success_flow(self):
        calls = []

        def fake_runner(code, args):
            calls.append((code, args))
            return {"output": "hello", "content_type": "text/plain"}

        server_execution.run_text_function = fake_runner

        server = types.SimpleNamespace(definition="print('hello')")

        first_result = server_execution.execute_server_code(server, "greet")
        second_result = server_execution.execute_server_code_from_definition("print('hello')", "greet")

        self.assertEqual(first_result, ("redirect", "/deadbeef"))
        self.assertEqual(second_result, first_result)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], server.definition)
        self.assertEqual(calls[1][0], "print('hello')")
        self.assertEqual(calls[0][1], calls[1][1])

    def test_execute_functions_share_error_flow(self):
        def failing_runner(code, args):
            raise ValueError("boom")

        server_execution.run_text_function = failing_runner

        server = types.SimpleNamespace(definition="print('fail')")

        first_response = server_execution.execute_server_code(server, "fail")
        second_response = server_execution.execute_server_code_from_definition("print('fail')", "fail")

        self.assertEqual(first_response.status_code, 500)
        self.assertEqual(second_response.status_code, 500)
        self.assertEqual(
            first_response.headers["Content-Type"], "text/html; charset=utf-8"
        )
        self.assertEqual(
            second_response.headers["Content-Type"], "text/html; charset=utf-8"
        )
        self.assertEqual(first_response.data, second_response.data)


if __name__ == "__main__":
    unittest.main()
