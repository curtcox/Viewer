import sys
import types
import unittest

# Lightweight module mocks so importing server_execution doesn't require external deps
mock_flask = types.ModuleType("flask")
mock_flask.Response = type('Response', (), {})  # Mock Response class
mock_flask.jsonify = lambda *a, **k: None
mock_flask.make_response = lambda x: types.SimpleNamespace(headers={}, status_code=200, data=x)
mock_flask.redirect = lambda url: ("redirect", url)
mock_flask.render_template = lambda *a, **k: ""
mock_flask.url_for = lambda *a, **k: "/mock/url"
mock_flask.request = types.SimpleNamespace(
    path="/", query_string=b"", remote_addr="127.0.0.1", user_agent=types.SimpleNamespace(string="UA"),
    headers={}, form={}, args={}, endpoint="ep", scheme="http", host="localhost", method="GET",
)
mock_flask.session = {}
mock_flask.current_app = types.SimpleNamespace(
    root_path="/mock/app", test_client=lambda: None, test_request_context=lambda **kw: None
)
mock_flask.has_app_context = lambda: False
mock_flask.has_request_context = lambda: False
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


class _ServerInvocationInput:
    def __init__(
        self,
        *,
        servers_cid=None,
        variables_cid=None,
        secrets_cid=None,
        request_details_cid=None,
        invocation_cid=None,
    ):
        self.servers_cid = servers_cid
        self.variables_cid = variables_cid
        self.secrets_cid = secrets_cid
        self.request_details_cid = request_details_cid
        self.invocation_cid = invocation_cid


mock_db_access.ServerInvocationInput = _ServerInvocationInput
sys.modules.setdefault("db_access", mock_db_access)

mock_runner = types.ModuleType("text_function_runner")
mock_runner.run_text_function = lambda code, args: {"output": "", "content_type": "text/html"}
sys.modules.setdefault("text_function_runner", mock_runner)

# Additional mocks for new decomposed modules
mock_cid_presenter = types.ModuleType("cid_presenter")
mock_cid_presenter.cid_path = lambda cid, ext=None: f"/{cid}" if not ext else f"/{cid}.{ext}"
mock_cid_presenter.format_cid = lambda x: x
sys.modules.setdefault("cid_presenter", mock_cid_presenter)

mock_alias_routing = types.ModuleType("alias_routing")
mock_alias_routing.find_matching_alias = lambda *a, **k: None
sys.modules.setdefault("alias_routing", mock_alias_routing)

mock_models = types.ModuleType("models")
mock_models.ServerInvocation = type('ServerInvocation', (), {})
sys.modules.setdefault("models", mock_models)

mock_syntax_highlighting = types.ModuleType("syntax_highlighting")
mock_syntax_highlighting.highlight_source = lambda *a, **k: ("", "")
sys.modules.setdefault("syntax_highlighting", mock_syntax_highlighting)

mock_werkzeug = types.ModuleType("werkzeug")
mock_werkzeug.routing = types.ModuleType("werkzeug.routing")
mock_werkzeug.routing.BuildError = Exception
sys.modules.setdefault("werkzeug", mock_werkzeug)
sys.modules.setdefault("werkzeug.routing", mock_werkzeug.routing)

mock_routes = types.ModuleType("routes")
mock_routes.source = types.ModuleType("routes.source")
mock_routes.source._get_tracked_paths = lambda *a, **k: frozenset()
sys.modules.setdefault("routes", mock_routes)
sys.modules.setdefault("routes.source", mock_routes.source)

mock_utils = types.ModuleType("utils")
mock_utils.stack_trace = types.ModuleType("utils.stack_trace")
mock_utils.stack_trace.build_stack_trace = lambda *a, **k: []
mock_utils.stack_trace.extract_exception = lambda exc: exc
sys.modules.setdefault("utils", mock_utils)
sys.modules.setdefault("utils.stack_trace", mock_utils.stack_trace)

mock_logfire = types.ModuleType("logfire")
mock_logfire.instrument = lambda *a, **k: lambda f: f  # Decorator that returns function unchanged
sys.modules.setdefault("logfire", mock_logfire)

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
        # Import submodules to patch where functions are used
        from server_execution import code_execution, response_handling, error_handling, invocation_tracking, variable_resolution

        # Save originals
        self.original_run_text_function = code_execution.run_text_function
        self.original_build_request_args = code_execution.build_request_args
        self.original_create_invocation = invocation_tracking.create_server_invocation_record
        self.original_make_response = error_handling.make_response
        self.original_redirect = response_handling.redirect
        self.original_create_cid_record = response_handling.create_cid_record
        self.original_get_cid_by_path = response_handling.get_cid_by_path
        self.original_generate_cid = response_handling.generate_cid
        self.original_get_extension = response_handling.get_extension_from_mime_type
        # After decomposition, current_user is only in variable_resolution
        self.original_current_user = variable_resolution.current_user
        self.original_render_error_html = error_handling._render_execution_error_html

        # Set mocks where they're used
        mock_user = types.SimpleNamespace(id="user-123")
        variable_resolution.current_user = mock_user
        code_execution.build_request_args = lambda: {
            "request": {"path": "/mock"},
            "context": {"variables": {}, "secrets": {}, "servers": {}},
        }
        invocation_tracking.create_server_invocation_record = lambda *a, **k: None
        response_handling.create_cid_record = lambda *a, **k: None
        response_handling.get_cid_by_path = lambda *a, **k: None
        response_handling.generate_cid = lambda b: "deadbeef"
        response_handling.get_extension_from_mime_type = (
            lambda ct: "html" if ct == "text/html" else ""
        )
        error_handling.make_response = lambda text: types.SimpleNamespace(
            headers={}, status_code=200, data=text
        )
        response_handling.redirect = lambda url: ("redirect", url)
        error_handling._render_execution_error_html = (
            lambda exc, code, args, server_name: "<html>Error</html>"
        )

        # Store modules for tearDown
        self.code_execution = code_execution
        self.response_handling = response_handling
        self.error_handling = error_handling
        self.invocation_tracking = invocation_tracking
        self.variable_resolution = variable_resolution

    def tearDown(self):
        self.code_execution.run_text_function = self.original_run_text_function
        self.code_execution.build_request_args = self.original_build_request_args
        self.invocation_tracking.create_server_invocation_record = self.original_create_invocation
        self.error_handling.make_response = self.original_make_response
        self.response_handling.redirect = self.original_redirect
        self.response_handling.create_cid_record = self.original_create_cid_record
        self.response_handling.get_cid_by_path = self.original_get_cid_by_path
        self.response_handling.generate_cid = self.original_generate_cid
        self.response_handling.get_extension_from_mime_type = self.original_get_extension
        # After decomposition, current_user is only in variable_resolution
        self.variable_resolution.current_user = self.original_current_user
        self.error_handling._render_execution_error_html = (
            self.original_render_error_html
        )

    def test_execute_functions_share_success_flow(self):
        calls = []

        def fake_runner(code, args):
            calls.append((code, args))
            return {"output": "hello", "content_type": "text/plain"}

        self.code_execution.run_text_function = fake_runner

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

        self.code_execution.run_text_function = failing_runner

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
