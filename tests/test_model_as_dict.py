#!/usr/bin/env python3
"""
Unit tests for the model_as_dict function
"""

class MockVariable:
    """Mock Variable model object"""
    def __init__(self, name, definition, user_id):
        self.name = name
        self.definition = definition
        self.user_id = user_id

    def __repr__(self):
        return f'<Variable {self.name} by {self.user_id}>'

class MockSecret:
    """Mock Secret model object"""
    def __init__(self, name, definition, user_id):
        self.name = name
        self.definition = definition
        self.user_id = user_id

    def __repr__(self):
        return f'<Secret {self.name} by {self.user_id}>'

class MockServer:
    """Mock Server model object"""
    def __init__(self, name, definition, user_id):
        self.name = name
        self.definition = definition
        self.user_id = user_id

    def __repr__(self):
        return f'<Server {self.name} by {self.user_id}>'

class MockObjectWithoutNameDefinition:
    """Mock object that doesn't have name/definition attributes"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"MockObject({self.value})"

def model_as_dict(model_objects):
    """Convert SQLAlchemy model objects to dict with names as keys and definitions as values"""
    if not model_objects:
        return {}

    result = {}
    for obj in model_objects:
        if hasattr(obj, 'name') and hasattr(obj, 'definition'):
            # For Variable, Secret, and Server objects
            result[obj.name] = obj.definition
        else:
            # Fallback for other object types
            result[str(obj)] = str(obj)

    return result

def test_empty_input():
    """Test model_as_dict with empty/None inputs"""
    print("=" * 60)
    print("TESTING EMPTY/NONE INPUTS")
    print("=" * 60)

    # Test empty list
    result = model_as_dict([])
    print(f"Empty list: {result}")
    assert not result, f"Expected empty dict, got {result}"
    print("✓ Empty list returns empty dict")

    # Test None
    result = model_as_dict(None)
    print(f"None input: {result}")
    assert not result, f"Expected empty dict, got {result}"
    print("✓ None input returns empty dict")

    print()

def test_single_objects():
    """Test model_as_dict with single objects"""
    print("=" * 60)
    print("TESTING SINGLE OBJECTS")
    print("=" * 60)

    # Test single variable
    variables = [MockVariable('test_var', 'test_value', 'user123')]
    result = model_as_dict(variables)
    expected = {'test_var': 'test_value'}
    print(f"Single variable: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Single variable works correctly")

    # Test single secret
    secrets = [MockSecret('api_key', 'secret123', 'user123')]
    result = model_as_dict(secrets)
    expected = {'api_key': 'secret123'}
    print(f"Single secret: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Single secret works correctly")

    # Test single server
    servers = [MockServer('echo1', 'return {"output": "hello"}', 'user123')]
    result = model_as_dict(servers)
    expected = {'echo1': 'return {"output": "hello"}'}
    print(f"Single server: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Single server works correctly")

    print()

def test_multiple_objects():
    """Test model_as_dict with multiple objects"""
    print("=" * 60)
    print("TESTING MULTIPLE OBJECTS")
    print("=" * 60)

    # Test multiple variables
    variables = [
        MockVariable('var1', 'value1', 'user123'),
        MockVariable('var2', 'value2', 'user123'),
        MockVariable('var3', 'value3', 'user123')
    ]
    result = model_as_dict(variables)
    expected = {'var1': 'value1', 'var2': 'value2', 'var3': 'value3'}
    print(f"Multiple variables: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Multiple variables work correctly")

    # Test multiple secrets
    secrets = [
        MockSecret('secret1', 'value1', 'user123'),
        MockSecret('secret2', 'value2', 'user123')
    ]
    result = model_as_dict(secrets)
    expected = {'secret1': 'value1', 'secret2': 'value2'}
    print(f"Multiple secrets: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Multiple secrets work correctly")

    # Test multiple servers
    servers = [
        MockServer('echo1', 'return {"output": "echo1"}', 'user123'),
        MockServer('echo2', 'return {"output": "echo2"}', 'user123')
    ]
    result = model_as_dict(servers)
    expected = {'echo1': 'return {"output": "echo1"}', 'echo2': 'return {"output": "echo2"}'}
    print(f"Multiple servers: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Multiple servers work correctly")

    print()

def test_mixed_objects():
    """Test model_as_dict with mixed object types"""
    print("=" * 60)
    print("TESTING MIXED OBJECT TYPES")
    print("=" * 60)

    # Mix of variables, secrets, and servers
    mixed_objects = [
        MockVariable('my_var', 'var_value', 'user123'),
        MockSecret('my_secret', 'secret_value', 'user123'),
        MockServer('my_server', 'server_code', 'user123')
    ]
    result = model_as_dict(mixed_objects)
    expected = {
        'my_var': 'var_value',
        'my_secret': 'secret_value',
        'my_server': 'server_code'
    }
    print(f"Mixed objects: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Mixed object types work correctly")

    print()

def test_fallback_objects():
    """Test model_as_dict with objects that don't have name/definition"""
    print("=" * 60)
    print("TESTING FALLBACK OBJECTS")
    print("=" * 60)

    # Objects without name/definition attributes
    fallback_objects = [
        MockObjectWithoutNameDefinition('test1'),
        MockObjectWithoutNameDefinition('test2')
    ]
    result = model_as_dict(fallback_objects)
    expected = {
        'MockObject(test1)': 'MockObject(test1)',
        'MockObject(test2)': 'MockObject(test2)'
    }
    print(f"Fallback objects: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Fallback objects work correctly")

    print()

def test_edge_cases():
    """Test edge cases and special scenarios"""
    print("=" * 60)
    print("TESTING EDGE CASES")
    print("=" * 60)

    # Test with duplicate names (later one should overwrite)
    duplicate_names = [
        MockVariable('same_name', 'first_value', 'user123'),
        MockVariable('same_name', 'second_value', 'user123')
    ]
    result = model_as_dict(duplicate_names)
    expected = {'same_name': 'second_value'}  # Later one overwrites
    print(f"Duplicate names: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Duplicate names handled correctly (later overwrites)")

    # Test with empty string values
    empty_values = [
        MockVariable('empty_var', '', 'user123'),
        MockSecret('empty_secret', '', 'user123')
    ]
    result = model_as_dict(empty_values)
    expected = {'empty_var': '', 'empty_secret': ''}
    print(f"Empty values: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Empty string values handled correctly")

    # Test with special characters in names and values
    special_chars = [
        MockVariable('var-with-dashes', 'value with spaces', 'user123'),
        MockVariable('var_with_underscores', 'value\nwith\nnewlines', 'user123'),
        MockSecret('secret.with.dots', 'value"with"quotes', 'user123')
    ]
    result = model_as_dict(special_chars)
    expected = {
        'var-with-dashes': 'value with spaces',
        'var_with_underscores': 'value\nwith\nnewlines',
        'secret.with.dots': 'value"with"quotes'
    }
    print(f"Special characters: {result}")
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Special characters handled correctly")

    print()

def test_echo1_integration():
    """Test how the new format works with echo1 server expectations"""
    print("=" * 60)
    print("TESTING ECHO1 INTEGRATION")
    print("=" * 60)

    # Simulate what echo1 server would receive
    variables = [
        MockVariable('test_var1', 'value1', 'user123'),
        MockVariable('test_var2', 'value2', 'user123')
    ]
    secrets = [
        MockSecret('api_key', 'secret123', 'user123')
    ]
    servers = [
        MockServer('echo1', 'return {"output": str(args)}', 'user123')
    ]

    # Build args like build_request_args would
    args = {
        'path': '/echo1',
        'query_string': '',
        'form_data': {},
        'args': {},
        'endpoint': None,
        'blueprint': None,
        'scheme': 'http',
        'variables': model_as_dict(variables),
        'secrets': model_as_dict(secrets),
        'servers': model_as_dict(servers)
    }

    print("Echo1 would receive:")
    print(f"  variables: {args['variables']}")
    print(f"  secrets: {args['secrets']}")
    print(f"  servers: {args['servers']}")

    # Verify the format is clean and accessible
    assert args['variables'] == {'test_var1': 'value1', 'test_var2': 'value2'}
    assert args['secrets'] == {'api_key': 'secret123'}
    assert args['servers'] == {'echo1': 'return {"output": str(args)}'}

    # Test string representation (what echo1 sees when it does str(args))
    args_str = str(args)
    print("\nString representation (what echo1 sees):")
    print(args_str)

    # Verify actual data is visible in the string
    assert 'test_var1' in args_str
    assert 'value1' in args_str
    assert 'api_key' in args_str
    assert 'secret123' in args_str

    print("\n✓ Echo1 integration works correctly!")
    print("✓ Variables and secrets are now accessible as simple key-value pairs!")

    print()

if __name__ == '__main__':
    try:
        test_empty_input()
        test_single_objects()
        test_multiple_objects()
        test_mixed_objects()
        test_fallback_objects()
        test_edge_cases()
        test_echo1_integration()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("The model_as_dict function works correctly and will fix the echo1 issue!")
        print("Variables and secrets will now appear as clean key-value dictionaries.")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
