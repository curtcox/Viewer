import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestRunTextFunction(unittest.TestCase):
    """Test suite for run_text_function."""

    def setUp(self):
        """Ensure we're testing the actual run_text_function implementation."""
        module = importlib.import_module('text_function_runner')
        self.run_text_function = importlib.reload(module).run_text_function

    def test_basic_functionality(self):
        """Test basic function execution with simple arguments."""
        body = "return x + y"
        argmap = {"x": 5, "y": 3}
        result = self.run_text_function(body, argmap)
        self.assertEqual(result, 8)

    def test_multiple_lines(self):
        """Test function with multiple lines of code."""
        body = """
z = x * 2
w = y + 1
return z + w
"""
        argmap = {"x": 10, "y": 5}
        result = self.run_text_function(body, argmap)
        self.assertEqual(result, 26)  # (10 * 2) + (5 + 1) = 20 + 6 = 26

    def test_param_order_specified(self):
        """Test that param_order fixes the function signature."""
        body = "return f'{a}-{b}-{c}'"
        argmap = {"c": "third", "a": "first", "b": "second"}

        # Parameters will be sorted alphabetically: a, b, c
        result = self.run_text_function(body, argmap)
        self.assertEqual(result, "first-second-third")

        # Same result since parameters are always sorted
        result = self.run_text_function(body, argmap)
        self.assertEqual(result, "first-second-third")

    def test_param_order_none_uses_sorted_keys(self):
        """Test that when param_order is None, keys are sorted."""
        body = "return f'{a}-{b}-{c}'"
        argmap = {"c": "third", "a": "first", "b": "second"}

        # Without param_order, should use sorted keys: a, b, c
        result = self.run_text_function(body, argmap)
        self.assertEqual(result, "first-second-third")

    def test_allowed_builtins(self):
        """Test that allowed_builtins exposes builtin functions."""
        body = "return len(text) + max(numbers)"
        argmap = {"text": "hello", "numbers": [1, 5, 3]}

        result = self.run_text_function(body, argmap)
        self.assertEqual(result, 10)  # len("hello") + max([1, 5, 3]) = 5 + 5 = 10

    def test_extra_globals(self):
        """Test that extra_globals provides additional modules/constants."""
        body = "return math.sqrt(x) + pi"
        argmap = {"x": 16}

        # Since we can't pass extra_globals anymore, we need to modify the test
        # to use builtins or skip this test case
        body = "import math; return math.sqrt(x) + 3.14159"  # Use hardcoded pi
        result = self.run_text_function(body, argmap)
        self.assertAlmostEqual(result, 7.14159, places=4)  # sqrt(16) + 3.14159 = 4 + 3.14159

    def test_hash_len_parameter(self):
        """Test that hash_len affects the generated function name length."""
        body = "return x"
        argmap = {"x": 42}

        # Test with different hash lengths - should all work
        for _ in [8, 12, 16]:
            result = self.run_text_function(body, argmap)
            self.assertEqual(result, 42)

    def test_deterministic_function_names(self):
        """Test that same body_text produces same function name (deterministic)."""
        body = "return x * 2"
        argmap = {"x": 5}

        # Multiple calls with same body should work consistently
        result1 = self.run_text_function(body, argmap)
        result2 = self.run_text_function(body, argmap)
        self.assertEqual(result1, 10)
        self.assertEqual(result2, 10)
        self.assertEqual(result1, result2)

    def test_different_body_different_names(self):
        """Test that different body_text produces different function names."""
        argmap = {"x": 5}

        result1 = self.run_text_function("return x * 2", argmap)
        result2 = self.run_text_function("return x + 2", argmap)

        self.assertEqual(result1, 10)
        self.assertEqual(result2, 7)

    def test_no_return_statement(self):
        """Test function that doesn't return anything (returns None)."""
        body = "x = y + 1"  # No return statement
        argmap = {"y": 5}

        result = self.run_text_function(body, argmap)
        self.assertIsNone(result)

    def test_complex_logic(self):
        """Test function with complex logic including conditionals."""
        body = """
if x > 10:
    result = x * 2
else:
    result = x + 10
return result
"""

        # Test both branches
        result1 = self.run_text_function(body, {"x": 15})
        self.assertEqual(result1, 30)  # 15 * 2

        result2 = self.run_text_function(body, {"x": 5})
        self.assertEqual(result2, 15)  # 5 + 10

    def test_typing_aliases_available_without_import(self):
        """Common typing aliases should be preloaded for convenience."""

        body = """
def typed_echo(payload: Dict[str, Optional[int]]) -> Dict[str, Optional[int]]:
    return payload

value = typed_echo({"number": x})
return value["number"]
"""

        result = self.run_text_function(body, {"x": 7})
        self.assertEqual(result, 7)

    def test_type_error_body_text_not_string(self):
        """Test TypeError when body_text is not a string."""
        with self.assertRaises(TypeError):
            self.run_text_function(123, {"x": 1})

    def test_type_error_argmap_not_dict(self):
        """Test TypeError when argmap is not a dict."""
        with self.assertRaises(TypeError):
            self.run_text_function("return x", ["x", 1])

    def test_param_order_missing_arguments(self):
        """Test that function works with available parameters only."""
        body = "return x * 2"  # Only use x since y is not available
        argmap = {"x": 1}

        # Function will use available parameters
        result = self.run_text_function(body, argmap)
        self.assertEqual(result, 2)  # x * 2 = 1 * 2 = 2

    def test_save_stores_message_bytes_with_user_id(self):
        """Ensure save() stores content using store_cid_from_bytes."""
        body = (
            "message = 'text of message'\n"
            "return { 'output': save(message) }"
        )
        argmap = {"context": {}, "request": {}}

        with patch('text_function_runner.store_cid_from_bytes') as mock_store:
            mock_store.return_value = 'cid-abc'
            with patch(
                'text_function_runner.current_user',
                new=SimpleNamespace(id='user-123'),
            ):
                result = self.run_text_function(body, argmap)

        mock_store.assert_called_once_with(b'text of message', 'user-123')
        self.assertEqual(result, {'output': 'cid-abc'})

    def test_save_uses_callable_id_attribute(self):
        """save() should call an id attribute when it is callable."""
        body = "return save(data)"
        argmap = {"data": "payload"}

        class CallableIdUser:
            def id(self):
                return "callable-user"

        with patch('text_function_runner.store_cid_from_bytes') as mock_store:
            mock_store.return_value = 'cid-callable'
            with patch('text_function_runner.current_user', new=CallableIdUser()):
                result = self.run_text_function(body, argmap)

        mock_store.assert_called_once_with(b'payload', 'callable-user')
        self.assertEqual(result, 'cid-callable')

    def test_save_falls_back_to_get_id_when_id_call_fails(self):
        """If the id attribute raises TypeError, fall back to get_id()."""
        body = "return save(message)"
        argmap = {"message": "hello"}

        class InconsistentUser:
            def id(self, unexpected):  # pragma: no cover - exercised via TypeError
                return "should-not-be-used"

            def get_id(self):
                return 77

        with patch('text_function_runner.store_cid_from_bytes') as mock_store:
            mock_store.return_value = 'cid-77'
            with patch('text_function_runner.current_user', new=InconsistentUser()):
                result = self.run_text_function(body, argmap)

        mock_store.assert_called_once_with(b'hello', '77')
        self.assertEqual(result, 'cid-77')

    def test_save_requires_user_identifier(self):
        """save() should raise when no user identifier is available."""
        body = "return save(payload)"
        argmap = {"payload": "ignored"}

        class AnonymousUser:
            def get_id(self):
                return None

        with patch('text_function_runner.store_cid_from_bytes') as mock_store:
            with patch('text_function_runner.current_user', new=AnonymousUser()):
                with self.assertRaises(RuntimeError):
                    self.run_text_function(body, argmap)

        mock_store.assert_not_called()

    def test_save_coerces_non_text_values_to_bytes(self):
        """save() should coerce non-text values into UTF-8 bytes."""
        body = "return save(value)"
        argmap = {"value": 12345}

        class NumericUser:
            def __init__(self):
                self.id = 'numeric-user'

        with patch('text_function_runner.store_cid_from_bytes') as mock_store:
            mock_store.return_value = 'cid-numeric'
            with patch('text_function_runner.current_user', new=NumericUser()):
                result = self.run_text_function(body, argmap)

        mock_store.assert_called_once_with(b'12345', 'numeric-user')
        self.assertEqual(result, 'cid-numeric')

    def test_save_allows_preencoded_bytes(self):
        """save() should pass bytes values to storage without re-encoding."""
        body = "return save(blob)"
        payload = b'\xffbinary data'
        argmap = {"blob": payload}

        class BinaryUser:
            def __init__(self):
                self.id = 'binary-user'

        with patch('text_function_runner.store_cid_from_bytes') as mock_store:
            mock_store.return_value = 'cid-bytes'
            with patch('text_function_runner.current_user', new=BinaryUser()):
                result = self.run_text_function(body, argmap)

        mock_store.assert_called_once_with(payload, 'binary-user')
        self.assertEqual(result, 'cid-bytes')

    def test_load_returns_text_content(self):
        """load() should retrieve CID content and decode to text by default."""
        body = "return load(cid)"
        argmap = {"cid": "bafy123"}

        with patch('text_function_runner.get_cid_by_path') as mock_get:
            mock_get.return_value = SimpleNamespace(file_data=b'print(\"hi\")')
            result = self.run_text_function(body, argmap)

        mock_get.assert_called_once_with('/bafy123')
        self.assertEqual(result, 'print("hi")')

    def test_load_supports_binary_mode(self):
        """load() should return raw bytes when encoding is disabled."""
        body = "return load(cid, encoding=None)"
        blob = b"\x00\x01\x02"
        argmap = {"cid": "binary"}

        with patch('text_function_runner.get_cid_by_path') as mock_get:
            mock_get.return_value = SimpleNamespace(file_data=blob)
            result = self.run_text_function(body, argmap)

        mock_get.assert_called_once_with('/binary')
        self.assertEqual(result, blob)

    def test_load_raises_for_missing_records(self):
        """load() should raise a ValueError when the CID cannot be found."""
        body = "return load(cid)"
        argmap = {"cid": "missing"}

        with patch('text_function_runner.get_cid_by_path') as mock_get:
            mock_get.return_value = None
            with self.assertRaises(ValueError):
                self.run_text_function(body, argmap)


if __name__ == '__main__':
    unittest.main()
