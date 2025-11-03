"""Tests for :func:`routes.servers._extract_context_references`."""

from __future__ import annotations

from routes.servers import _extract_context_references


def test_returns_empty_collections_for_blank_definitions() -> None:
    """Missing or empty definitions should result in empty lists."""

    assert _extract_context_references(None) == {"variables": [], "secrets": []}
    assert _extract_context_references("") == {"variables": [], "secrets": []}


def test_detects_direct_and_alias_based_context_usage() -> None:
    """Variables and secrets accessed directly or via aliases should be reported."""

    definition = """
variables_alias = context['variables']
secrets_alias = context.get('secrets', {})

direct_var = context['variables']['direct']
explicit_secret = context['secrets'].get('explicit')

alias_index = variables_alias['alias-index']
alias_get = variables_alias.get('alias-get')

token = secrets_alias.get('token')
password = secrets_alias['password']

# Duplicate references should not change the outcome
extra_direct = context['variables']['direct']
unused = secrets_alias.get('token')
"""

    references = _extract_context_references(definition)

    assert references["variables"] == ["alias-get", "alias-index", "direct"]
    assert references["secrets"] == ["explicit", "password", "token"]


def test_alias_matching_requires_word_boundaries() -> None:
    """Accesses using identifiers that merely contain an alias should be ignored."""

    definition = """
vars = context['variables']
secret_alias = context['secrets']

city = vars['city']
# These should not match because the alias is part of a larger identifier
other = myvars['country']
ignored = secret_alias_extra.get('ignored')

token = secret_alias.get('token')
"""

    references = _extract_context_references(definition)

    assert references["variables"] == ["city"]
    assert references["secrets"] == ["token"]


def test_ignores_other_context_keys() -> None:
    """Access to context keys other than 'variables' or 'secrets' should be ignored."""

    definition = """
other = context['other']
value = other['value']

settings = context.get('settings')
name = settings.get('name')
"""
    references = _extract_context_references(definition)

    assert references["variables"] == []
    assert references["secrets"] == []


def test_handles_complex_aliasing_scenarios() -> None:
    """References should be detected even with multiple levels of aliasing."""

    definition = """
v = context['variables']
s = context.get('secrets')

vars_alias = v
secrets_alias = s

first_name = vars_alias['first_name']
api_key = secrets_alias.get('api_key')
"""
    references = _extract_context_references(definition)

    assert references["variables"] == ["first_name"]
    assert references["secrets"] == ["api_key"]


def test_ignores_unused_aliases() -> None:
    """Aliases that are defined but not used to access context values should be ignored."""

    definition = """
variables_alias = context['variables']
secrets_alias = context.get('secrets', {})

# These aliases are not used, so they should not result in any references
unused_variables = context.get('variables')
unused_secrets = context['secrets']

city = variables_alias['city']
token = secrets_alias.get('token')
"""
    references = _extract_context_references(definition)

    assert references["variables"] == ["city"]
    assert references["secrets"] == ["token"]


def test_includes_known_variables_and_secrets_from_parameters() -> None:
    """Names from known_variables and known_secrets appearing as parameter names
    in the server's main function should be reported as references.
    """

    definition = """
def main(name: str, email: str, api_key: str, Auth: str):
    return f"Hello {name} <{email}> using {api_key} with {Auth}"
"""
    references = _extract_context_references(
        definition,
        known_variables=["name", "email", "unused_variable"],
        known_secrets=["api_key", "Auth", "unused_secret"],
    )

    assert references["variables"] == ["email", "name"]
    assert references["secrets"] == ["Auth", "api_key"]
