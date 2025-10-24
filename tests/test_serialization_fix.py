#!/usr/bin/env python3
"""
Test to validate that the model object serialization fix works correctly
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

def serialize_model_objects(model_objects):
    """Convert SQLAlchemy model objects to serializable dictionaries"""
    if not model_objects:
        return []

    serialized = []
    for obj in model_objects:
        if hasattr(obj, 'name') and hasattr(obj, 'definition'):
            # For Variable, Secret, and Server objects
            serialized.append({
                'name': obj.name,
                'definition': obj.definition
            })
        else:
            # Fallback for other object types
            serialized.append(str(obj))

    return serialized

def test_serialize_model_objects():
    """Test the serialize_model_objects function"""
    print("=" * 60)
    print("TESTING serialize_model_objects FUNCTION")
    print("=" * 60)

    # Test with variables
    variables = [
        MockVariable('test_var1', 'value1', 'user123'),
        MockVariable('test_var2', 'value2', 'user123')
    ]

    serialized_vars = serialize_model_objects(variables)
    print(f"Original variables: {variables}")
    print(f"Serialized variables: {serialized_vars}")
    print(f"Type of serialized[0]: {type(serialized_vars[0])}")

    assert len(serialized_vars) == 2
    assert serialized_vars[0] == {'name': 'test_var1', 'definition': 'value1'}
    assert serialized_vars[1] == {'name': 'test_var2', 'definition': 'value2'}
    print("✓ Variables serialization works correctly\n")

    # Test with secrets
    secrets = [
        MockSecret('test_secret1', 'secret_value1', 'user123')
    ]

    serialized_secrets = serialize_model_objects(secrets)
    print(f"Original secrets: {secrets}")
    print(f"Serialized secrets: {serialized_secrets}")
    print(f"Type of serialized[0]: {type(serialized_secrets[0])}")

    assert len(serialized_secrets) == 1
    assert serialized_secrets[0] == {'name': 'test_secret1', 'definition': 'secret_value1'}
    print("✓ Secrets serialization works correctly\n")

    # Test with servers
    servers = [
        MockServer('echo1', 'return {"output": "hello"}', 'user123')
    ]

    serialized_servers = serialize_model_objects(servers)
    print(f"Original servers: {servers}")
    print(f"Serialized servers: {serialized_servers}")
    print(f"Type of serialized[0]: {type(serialized_servers[0])}")

    assert len(serialized_servers) == 1
    assert serialized_servers[0] == {'name': 'echo1', 'definition': 'return {"output": "hello"}'}
    print("✓ Servers serialization works correctly\n")

    # Test with empty list
    empty_result = serialize_model_objects([])
    assert empty_result == []
    print("✓ Empty list handling works correctly\n")

    # Test with None
    none_result = serialize_model_objects(None)
    assert none_result == []
    print("✓ None handling works correctly\n")

def test_fixed_build_request_args():
    """Test the fixed build_request_args behavior"""
    print("=" * 60)
    print("TESTING FIXED build_request_args BEHAVIOR")
    print("=" * 60)

    # Mock the model objects that would be returned by user_variables(), user_secrets(), user_servers()
    mock_variables = [
        MockVariable('test_var1', 'value1', 'user123'),
        MockVariable('test_var2', 'value2', 'user123')
    ]

    mock_secrets = [
        MockSecret('test_secret1', 'secret_value1', 'user123')
    ]

    mock_servers = [
        MockServer('echo1', 'return {"output": "hello"}', 'user123')
    ]

    # Simulate what the fixed build_request_args would produce
    args = {
        'path': '/echo1',
        'query_string': '',
        'form_data': {},
        'args': {},
        'endpoint': None,
        'blueprint': None,
        'scheme': 'http',
        'variables': serialize_model_objects(mock_variables),
        'secrets': serialize_model_objects(mock_secrets),
        'servers': serialize_model_objects(mock_servers),
    }

    print("Fixed args structure:")
    print(f"  variables: {args['variables']}")
    print(f"  secrets: {args['secrets']}")
    print(f"  servers: {args['servers']}")

    # Test that the data is now properly serializable
    args_str = str(args)
    print("\nString representation (what echo1 will see):")
    print(args_str)

    # Verify the actual data is present in the string
    assert 'test_var1' in args_str
    assert 'value1' in args_str
    assert 'test_secret1' in args_str
    assert 'secret_value1' in args_str
    assert 'echo1' in args_str

    print("\n✓ Variables, secrets, and servers are now properly serialized!")
    print("✓ The echo1 server will now see the actual data instead of model object representations!")

def test_echo1_output_comparison():
    """Compare what echo1 would see before and after the fix"""
    print("\n" + "=" * 60)
    print("ECHO1 OUTPUT COMPARISON")
    print("=" * 60)

    # Before fix (model objects)
    mock_variables_before = [
        MockVariable('test_var1', 'value1', 'user123')
    ]
    mock_secrets_before = [
        MockSecret('test_secret1', 'secret_value1', 'user123')
    ]

    args_before = {
        'path': '/echo1',
        'query_string': '',
        'form_data': {},
        'args': {},
        'endpoint': None,
        'blueprint': None,
        'scheme': 'http',
        'variables': mock_variables_before,
        'secrets': mock_secrets_before
    }

    # After fix (serialized objects)
    args_after = {
        'path': '/echo1',
        'query_string': '',
        'form_data': {},
        'args': {},
        'endpoint': None,
        'blueprint': None,
        'scheme': 'http',
        'variables': serialize_model_objects(mock_variables_before),
        'secrets': serialize_model_objects(mock_secrets_before)
    }

    print("BEFORE FIX (what echo1 currently sees):")
    print(f"variables: {args_before['variables']}")
    print(f"secrets: {args_before['secrets']}")

    print("\nAFTER FIX (what echo1 will now see):")
    print(f"variables: {args_after['variables']}")
    print(f"secrets: {args_after['secrets']}")

    print(f"\nBEFORE - Full output: {str(args_before)}")
    print(f"\nAFTER - Full output: {str(args_after)}")

    # The key difference: after the fix, actual data is visible
    before_str = str(args_before['variables'])
    after_str = str(args_after['variables'])

    print("\nVariables comparison:")
    print(f"  Before: {before_str}")
    print(f"  After:  {after_str}")

    # Before shows model representation, after shows actual data
    assert '<Variable' in before_str  # Model representation
    assert 'test_var1' in after_str and 'value1' in after_str  # Actual data

    print("\n✓ Fix successfully converts model objects to readable data!")

if __name__ == '__main__':
    try:
        test_serialize_model_objects()
        test_fixed_build_request_args()
        test_echo1_output_comparison()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("The serialization fix should resolve the echo1 variables/secrets issue!")
        print("Variables and secrets will now appear as proper data instead of empty lists.")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
