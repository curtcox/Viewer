#!/usr/bin/env python3
"""
Simple test to demonstrate the variables and secrets serialization issue
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

def test_current_behavior():
    """Test what currently happens with variables and secrets"""
    print("=" * 60)
    print("CURRENT BEHAVIOR - Model Objects")
    print("=" * 60)

    # This mimics what the legacy list_variables()/list_secrets() helpers returned
    variables = [
        MockVariable('test_var1', 'value1', 'user123'),
        MockVariable('test_var2', 'value2', 'user123')
    ]

    secrets = [
        MockSecret('test_secret1', 'secret_value1', 'user123')
    ]

    # This is what gets passed to the echo1 server
    args = {
        'path': '/echo1',
        'query_string': '',
        'form_data': {},
        'args': {},
        'endpoint': None,
        'blueprint': None,
        'scheme': 'http',
        'variables': variables,
        'secrets': secrets
    }

    print(f"Variables: {variables}")
    print(f"Secrets: {secrets}")
    print(f"Type of variables[0]: {type(variables[0])}")
    print(f"Type of secrets[0]: {type(secrets[0])}")

    # When the echo1 server does str(args), this is what happens:
    args_str = str(args)
    print("\nString representation (what echo1 sees):")
    print(args_str)

    # The variables and secrets show as model representations, not their data
    print(f"\nVariables in string: {str(variables)}")
    print(f"Secrets in string: {str(secrets)}")

    # Assertions and return
    assert len(variables) == 2
    assert len(secrets) == 1
    return args

def test_expected_behavior():
    """Test what should happen with variables and secrets"""
    print("\n" + "=" * 60)
    print("EXPECTED BEHAVIOR - Serializable Data")
    print("=" * 60)

    # This is what should be passed to servers
    variables = [
        {'name': 'test_var1', 'definition': 'value1'},
        {'name': 'test_var2', 'definition': 'value2'}
    ]

    secrets = [
        {'name': 'test_secret1', 'definition': 'secret_value1'}
    ]

    args = {
        'path': '/echo1',
        'query_string': '',
        'form_data': {},
        'args': {},
        'endpoint': None,
        'blueprint': None,
        'scheme': 'http',
        'variables': variables,
        'secrets': secrets
    }

    print(f"Variables: {variables}")
    print(f"Secrets: {secrets}")
    print(f"Type of variables[0]: {type(variables[0])}")
    print(f"Type of secrets[0]: {type(secrets[0])}")

    # When the echo1 server does str(args), this shows meaningful data:
    args_str = str(args)
    print("\nString representation (what echo1 should see):")
    print(args_str)

    # The variables and secrets show actual data
    print(f"\nVariables in string: {str(variables)}")
    print(f"Secrets in string: {str(secrets)}")

    # Assertions and return
    assert len(variables) == 2
    assert len(secrets) == 1
    return args

def demonstrate_issue():
    """Demonstrate the core issue"""
    print("\n" + "=" * 60)
    print("ISSUE DEMONSTRATION")
    print("=" * 60)

    current_args = test_current_behavior()
    expected_args = test_expected_behavior()

    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)

    print("Current variables output:")
    print(f"  {current_args['variables']}")

    print("Expected variables output:")
    print(f"  {expected_args['variables']}")

    print("\nCurrent secrets output:")
    print(f"  {current_args['secrets']}")

    print("Expected secrets output:")
    print(f"  {expected_args['secrets']}")

    print("\n" + "=" * 60)
    print("ROOT CAUSE")
    print("=" * 60)
    print("The list_variables() and list_secrets() helpers return SQLAlchemy model objects")
    print("instead of serializable dictionaries. When the echo1 server calls str() on the")
    print("arguments, it gets model object representations like '<Variable test_var1 by user123>'")
    print("instead of the actual variable data like {'name': 'test_var1', 'definition': 'value1'}")

if __name__ == '__main__':
    demonstrate_issue()
