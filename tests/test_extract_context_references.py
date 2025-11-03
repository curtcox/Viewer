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
