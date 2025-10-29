"""Integration tests ensuring alias and server responses ignore user identity."""
from __future__ import annotations

from typing import Optional

from db_access import get_alias_by_name, get_server_by_name


def _set_user_session(client, user_id: Optional[str]) -> None:
    with client.session_transaction() as session:
        session.pop('_user_id', None)
        session.pop('_fresh', None)
        if user_id is not None:
            session['_user_id'] = user_id
            session['_fresh'] = True


def test_alias_creation_redirects_consistently(client):
    alias_name = 'shared-alias'
    payload = {
        'name': alias_name,
        'definition': f'{alias_name} -> /servers/echo',
        'enabled': 'y',
        'submit': 'Save Alias',
    }

    response_default = client.post('/aliases/new', data=payload, follow_redirects=False)
    assert response_default.status_code == 302
    assert response_default.headers['Location'] == '/aliases'

    default_alias = get_alias_by_name('default-user', alias_name)
    assert default_alias is not None

    _set_user_session(client, 'alternate-user')
    response_alternate = client.post('/aliases/new', data=payload, follow_redirects=False)
    assert response_alternate.status_code == response_default.status_code
    assert response_alternate.headers['Location'] == response_default.headers['Location']

    alternate_alias = get_alias_by_name('alternate-user', alias_name)
    assert alternate_alias is not None
    assert alternate_alias.definition == default_alias.definition


def test_server_creation_redirects_consistently(client):
    server_name = 'shared-server'
    definition = 'def main(**kwargs):\n    return "hello"'
    payload = {
        'name': server_name,
        'definition': definition,
        'enabled': 'y',
        'submit': 'Save Server',
    }

    response_default = client.post('/servers/new', data=payload, follow_redirects=False)
    assert response_default.status_code == 302
    assert response_default.headers['Location'] == '/servers'

    default_server = get_server_by_name('default-user', server_name)
    assert default_server is not None

    _set_user_session(client, 'alternate-user')
    response_alternate = client.post('/servers/new', data=payload, follow_redirects=False)
    assert response_alternate.status_code == response_default.status_code
    assert response_alternate.headers['Location'] == response_default.headers['Location']

    alternate_server = get_server_by_name('alternate-user', server_name)
    assert alternate_server is not None
    assert alternate_server.definition == default_server.definition
