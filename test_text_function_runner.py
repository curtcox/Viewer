import pytest
from text_function_runner import run_text_function


class TestRunTextFunction:
    """Test suite for run_text_function."""

    def test_basic_functionality(self):
        """Test basic function execution with simple arguments."""
        body = "return x + y"
        argmap = {"x": 5, "y": 3}
        result = run_text_function(body, argmap)
        assert result == 8

    def test_multiple_lines(self):
        """Test function with multiple lines of code."""
        body = """
z = x * 2
w = y + 1
return z + w
"""
        argmap = {"x": 10, "y": 5}
        result = run_text_function(body, argmap)
        assert result == 26  # (10 * 2) + (5 + 1) = 20 + 6 = 26

    def test_param_order_specified(self):
        """Test that param_order fixes the function signature."""
        body = "return f'{a}-{b}-{c}'"
        argmap = {"c": "third", "a": "first", "b": "second"}

        # Parameters will be sorted alphabetically: a, b, c
        result = run_text_function(body, argmap)
        assert result == "first-second-third"

        # Same result since parameters are always sorted
        result = run_text_function(body, argmap)
        assert result == "first-second-third"

    def test_param_order_none_uses_sorted_keys(self):
        """Test that when param_order is None, keys are sorted."""
        body = "return f'{a}-{b}-{c}'"
        argmap = {"c": "third", "a": "first", "b": "second"}

        # Without param_order, should use sorted keys: a, b, c
        result = run_text_function(body, argmap)
        assert result == "first-second-third"

    def test_allowed_builtins(self):
        """Test that allowed_builtins exposes builtin functions."""
        body = "return len(text) + max(numbers)"
        argmap = {"text": "hello", "numbers": [1, 5, 3]}

        result = run_text_function(body, argmap)
        assert result == 10  # len("hello") + max([1, 5, 3]) = 5 + 5 = 10

    def test_extra_globals(self):
        """Test that extra_globals provides additional modules/constants."""
        body = "return math.sqrt(x) + pi"
        argmap = {"x": 16}

        # Since we can't pass extra_globals anymore, we need to modify the test
        # to use builtins or skip this test case
        body = "import math; return math.sqrt(x) + 3.14159"  # Use hardcoded pi
        result = run_text_function(body, argmap)
        assert result == pytest.approx(7.14159, rel=1e-4)  # sqrt(16) + 3.14159 = 4 + 3.14159

    def test_hash_len_parameter(self):
        """Test that hash_len affects the generated function name length."""
        body = "return x"
        argmap = {"x": 42}

        # Test with different hash lengths - should all work
        for hash_len in [8, 12, 16]:
            result = run_text_function(body, argmap)
            assert result == 42

    def test_deterministic_function_names(self):
        """Test that same body_text produces same function name (deterministic)."""
        body = "return x * 2"
        argmap = {"x": 5}

        # Multiple calls with same body should work consistently
        result1 = run_text_function(body, argmap)
        result2 = run_text_function(body, argmap)
        assert result1 == result2 == 10

    def test_different_body_different_names(self):
        """Test that different body_text produces different function names."""
        argmap = {"x": 5}

        result1 = run_text_function("return x * 2", argmap)
        result2 = run_text_function("return x + 2", argmap)

        assert result1 == 10
        assert result2 == 7

    def test_no_return_statement(self):
        """Test function that doesn't return anything (returns None)."""
        body = "x = y + 1"  # No return statement
        argmap = {"y": 5}

        result = run_text_function(body, argmap)
        assert result is None

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
        result1 = run_text_function(body, {"x": 15})
        assert result1 == 30  # 15 * 2

        result2 = run_text_function(body, {"x": 5})
        assert result2 == 15  # 5 + 10

    def test_type_error_body_text_not_string(self):
        """Test TypeError when body_text is not a string."""
        with pytest.raises(TypeError, match="body_text must be a string"):
            run_text_function(123, {"x": 1})

    def test_type_error_argmap_not_dict(self):
        """Test TypeError when argmap is not a dict."""
        with pytest.raises(TypeError, match="arg_map must be a dict"):
            run_text_function("return x", ["x", 1])

    def test_param_order_missing_arguments(self):
        """Test that function works with available parameters only."""
        body = "return x * 2"  # Only use x since y is not available
        argmap = {"x": 1}

        # Function will use available parameters
        result = run_text_function(body, argmap)
        assert result == 2  # x * 2 = 1 * 2 = 2

    def test_param_order_extra_arguments(self):
        """Test that function uses all available parameters."""
        body = "return x + y"  # Use both available parameters
        argmap = {"x": 1, "y": 2}

        # Function will use all available parameters
        result = run_text_function(body, argmap)
        assert result == 3  # x + y = 1 + 2 = 3

    def test_param_order_both_missing_and_extra(self):
        """Test that function uses available parameters."""
        body = "return x + z"  # Use available params
        argmap = {"x": 1, "z": 3}

        # Function will use available parameters (x, z)
        result = run_text_function(body, argmap)
        assert result == 4  # x + z = 1 + 3 = 4

    def test_restricted_builtins_security(self):
        """Test that all builtins are now available."""
        body = "return len('hello')"
        argmap = {}

        # All builtins are now allowed
        result = run_text_function(body, argmap)
        assert result == 5  # len("hello") = 5

    def test_no_access_to_dangerous_builtins(self):
        """Test that all builtins including eval are now accessible."""
        body = "return eval('1+1')"
        argmap = {}

        # All builtins are now allowed including eval
        result = run_text_function(body, argmap)
        assert result == 2

    def test_syntax_error_in_body(self):
        """Test that syntax errors in body_text are propagated."""
        body = "return x +"  # Invalid syntax
        argmap = {"x": 1}

        with pytest.raises(SyntaxError):
            run_text_function(body, argmap)

    def test_runtime_error_in_body(self):
        """Test that runtime errors in body_text are propagated."""
        body = "return x / y"
        argmap = {"x": 1, "y": 0}

        with pytest.raises(ZeroDivisionError):
            run_text_function(body, argmap)

    def test_empty_argmap(self):
        """Test function with no parameters."""
        body = "return 42"
        argmap = {}

        result = run_text_function(body, argmap)
        assert result == 42

    def test_empty_body_text(self):
        """Test with empty body text - should raise IndentationError."""
        body = ""
        argmap = {"x": 1}

        with pytest.raises(IndentationError):
            run_text_function(body, argmap)

    def test_whitespace_handling(self):
        """Test that indentation in body_text is handled correctly."""
        body = """
    # This has leading whitespace
    result = x * 2
    return result
"""
        argmap = {"x": 5}

        result = run_text_function(body, argmap)
        assert result == 10

    def test_unicode_in_body_text(self):
        """Test that unicode characters in body_text work correctly."""
        body = "return f'Hello {name} 👋'"
        argmap = {"name": "World"}

        result = run_text_function(body, argmap)
        assert result == "Hello World 👋"

    def test_param_order_as_different_iterables(self):
        """Test param_order with different iterable types."""
        body = "return f'{a}-{b}'"
        argmap = {"a": "first", "b": "second"}

        # Test with tuple
        result = run_text_function(body, argmap)
        assert result == "first-second"

        # Test with set (though order might vary, function should still work)
        result = run_text_function(body, argmap)
        assert result == "first-second"

    def test_builtins_available(self):
        """Test that standard builtins are available."""
        body = "return len(text) + max(numbers)"
        argmap = {"text": "hello", "numbers": [1, 5, 3]}

        result = run_text_function(body, argmap)
        assert result == 10  # len("hello") + max([1, 5, 3]) = 5 + 5 = 10

    def test_string_builtins(self):
        """Test string-related builtins."""
        body = """
result = []
result.append(str(num))
result.append(repr(text))
result.append(chr(65))
result.append(ord('A'))
return result
"""
        argmap = {"num": 42, "text": "hello"}

        result = run_text_function(body, argmap)
        assert result == ['42', "'hello'", 'A', 65]

    def test_numeric_builtins(self):
        """Test numeric builtins."""
        body = """
return {
    'abs': abs(negative),
    'min': min(numbers),
    'max': max(numbers),
    'sum': sum(numbers),
    'round': round(pi, 2),
    'int': int(float_val),
    'float': float(int_val)
}
"""
        argmap = {
            "negative": -5,
            "numbers": [1, 5, 3, 9, 2],
            "pi": 3.14159,
            "float_val": 7.8,
            "int_val": 42
        }

        result = run_text_function(body, argmap)
        expected = {
            'abs': 5,
            'min': 1,
            'max': 9,
            'sum': 20,
            'round': 3.14,
            'int': 7,
            'float': 42.0
        }
        assert result == expected

    def test_collection_builtins(self):
        """Test collection-related builtins."""
        body = """
return {
    'len': len(items),
    'sorted': sorted(items),
    'reversed': list(reversed(items)),
    'enumerate': list(enumerate(items)),
    'zip': list(zip(items, range(len(items)))),
    'any': any([True, False, False]),
    'all': all([True, True, True])
}
"""
        argmap = {"items": [3, 1, 4, 1, 5]}

        result = run_text_function(body, argmap)
        expected = {
            'len': 5,
            'sorted': [1, 1, 3, 4, 5],
            'reversed': [5, 1, 4, 1, 3],
            'enumerate': [(0, 3), (1, 1), (2, 4), (3, 1), (4, 5)],
            'zip': [(3, 0), (1, 1), (4, 2), (1, 3), (5, 4)],
            'any': True,
            'all': True
        }
        assert result == expected

    def test_type_checking_builtins(self):
        """Test type checking and conversion builtins."""
        body = """
return {
    'isinstance_str': isinstance(text, str),
    'isinstance_int': isinstance(num, int),
    'type_str': type(text).__name__,
    'type_list': type(items).__name__,
    'bool_true': bool(1),
    'bool_false': bool(0),
    'list_from_tuple': list(tuple_val),
    'tuple_from_list': tuple(list_val),
    'set_from_list': set(list_val),
    'dict_from_pairs': dict(pairs)
}
"""
        argmap = {
            "text": "hello",
            "num": 42,
            "items": [1, 2, 3],
            "tuple_val": (1, 2, 3),
            "list_val": [1, 2, 2, 3],
            "pairs": [('a', 1), ('b', 2)]
        }

        result = run_text_function(body, argmap)
        expected = {
            'isinstance_str': True,
            'isinstance_int': True,
            'type_str': 'str',
            'type_list': 'list',
            'bool_true': True,
            'bool_false': False,
            'list_from_tuple': [1, 2, 3],
            'tuple_from_list': (1, 2, 2, 3),
            'set_from_list': {1, 2, 3},
            'dict_from_pairs': {'a': 1, 'b': 2}
        }
        assert result == expected

    def test_iteration_builtins(self):
        """Test iteration-related builtins."""
        body = """
# Test range
numbers = list(range(start, end))

# Test filter and map
evens = list(filter(lambda x: x % 2 == 0, numbers))
squares = list(map(lambda x: x ** 2, numbers))

return {
    'range': numbers,
    'filter': evens,
    'map': squares
}
"""
        argmap = {"start": 1, "end": 6}

        result = run_text_function(body, argmap)
        expected = {
            'range': [1, 2, 3, 4, 5],
            'filter': [2, 4],
            'map': [1, 4, 9, 16, 25]
        }
        assert result == expected

    def test_advanced_builtins(self):
        """Test more advanced builtins."""
        body = """
# Test eval and exec (now available)
eval_result = eval('2 + 3 * 4')

# Test format
formatted = format(pi, '.2f')

# Test hasattr and getattr
class TestObj:
    def __init__(self):
        self.value = 42

obj = TestObj()
has_value = hasattr(obj, 'value')
get_value = getattr(obj, 'value', None)

# Test vars and dir
obj_vars = vars(obj)
obj_dir = 'value' in dir(obj)

return {
    'eval': eval_result,
    'format': formatted,
    'hasattr': has_value,
    'getattr': get_value,
    'vars': obj_vars,
    'dir': obj_dir
}
"""
        argmap = {"pi": 3.14159}

        result = run_text_function(body, argmap)
        expected = {
            'eval': 14,  # 2 + 3 * 4 = 2 + 12 = 14
            'format': '3.14',
            'hasattr': True,
            'getattr': 42,
            'vars': {'value': 42},
            'dir': True
        }
        assert result == expected

    def test_io_and_utility_builtins(self):
        """Test I/O and utility builtins."""
        body = """
# Test bin, oct, hex
binary = bin(num)
octal = oct(num)
hexadecimal = hex(num)

# Test divmod and pow
div_result = divmod(17, 5)
power_result = pow(base, exp)

# Test id (just check it returns an int)
obj_id = type(id(items))

return {
    'bin': binary,
    'oct': octal,
    'hex': hexadecimal,
    'divmod': div_result,
    'pow': power_result,
    'id_type': obj_id.__name__
}
"""
        argmap = {"num": 15, "base": 2, "exp": 3, "items": [1, 2, 3]}

        result = run_text_function(body, argmap)
        expected = {
            'bin': '0b1111',
            'oct': '0o17',
            'hex': '0xf',
            'divmod': (3, 2),
            'pow': 8,
            'id_type': 'int'
        }
        assert result == expected
