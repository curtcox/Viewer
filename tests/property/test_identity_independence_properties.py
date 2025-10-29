"""Property-based tests verifying identity-independent behaviour."""
from __future__ import annotations

import string
from types import SimpleNamespace
from unittest.mock import patch

from hypothesis import assume, given, settings, strategies as st

from alias_definition import format_primary_alias_line
from alias_routing import find_matching_alias
from models import Alias, Server
from routes.entities import create_entity

_alphabet = string.ascii_lowercase + string.digits + "-_"
_non_empty_text = st.text(alphabet=_alphabet, min_size=1, max_size=10)


@settings(max_examples=50, deadline=None)
@given(alias_name=_non_empty_text, target_slug=_non_empty_text, other_user=_non_empty_text)
def test_alias_matching_independent_of_user(alias_name: str, target_slug: str, other_user: str) -> None:
    assume(other_user != 'default-user')

    path = f'/{alias_name}'
    target_path = f'/{target_slug}'
    definition = format_primary_alias_line('literal', f'/{alias_name}', target_path, alias_name=alias_name)

    default_alias = Alias(name=alias_name, user_id='default-user', definition=definition)
    default_alias.enabled = True
    alternate_alias = Alias(name=alias_name, user_id=other_user, definition=definition)
    alternate_alias.enabled = True

    with patch('alias_routing.get_user_aliases', return_value=[default_alias]):
        with patch('alias_routing.current_user', new=SimpleNamespace(id='default-user')):
            default_match = find_matching_alias(path)

    with patch('alias_routing.get_user_aliases', return_value=[alternate_alias]):
        with patch('alias_routing.current_user', new=SimpleNamespace(id=other_user)):
            alternate_match = find_matching_alias(path)

    assert default_match is not None
    assert alternate_match is not None
    assert default_match.route.target_path == alternate_match.route.target_path


_server_definition_text = st.text(alphabet=_alphabet + " \n", min_size=1, max_size=50)


@settings(max_examples=50, deadline=None)
@given(
    server_name=_non_empty_text,
    server_definition=_server_definition_text,
    first_user=_non_empty_text,
    second_user=_non_empty_text,
)
def test_server_creation_independent_of_user(
    server_name: str,
    server_definition: str,
    first_user: str,
    second_user: str,
) -> None:
    assume(first_user != second_user)

    form = SimpleNamespace(
        name=SimpleNamespace(data=server_name),
        definition=SimpleNamespace(data=server_definition),
        enabled=SimpleNamespace(data=True),
    )

    with patch('routes.entities.check_name_exists', side_effect=[False, False]) as mock_check, \
         patch('routes.entities.save_entity'), \
         patch('routes.entities.record_entity_interaction'), \
         patch('routes.entities.save_server_definition_as_cid', return_value='cid'), \
         patch('routes.servers.update_server_definitions_cid'), \
         patch('routes.entities.flash'):
        first_result = create_entity(Server, form, first_user, 'server')
        second_result = create_entity(Server, form, second_user, 'server')

    assert first_result is True
    assert second_result is True

    first_call_user = mock_check.call_args_list[0][0][2]
    second_call_user = mock_check.call_args_list[1][0][2]
    assert first_call_user == first_user
    assert second_call_user == second_user
