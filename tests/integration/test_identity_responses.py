"""Integration tests ensuring alias and server responses ignore user identity."""
from __future__ import annotations

from typing import Optional

from unittest.mock import patch

from database import db
from db_access import get_alias_by_name, get_server_by_name
import identity


def _set_user_session(client, user_id: Optional[str]) -> None:
    with client.session_transaction() as session:
        session.pop('_user_id', None)
        session.pop('_fresh', None)
        if user_id is not None:
            session['_user_id'] = user_id
            session['_fresh'] = True


def _collect_css_redirect_chain(client):
    hops: list[tuple[int, Optional[str]]] = []
    response = client.get('/css/custom.css', follow_redirects=False)
    hops.append((response.status_code, response.headers.get('Location')))

    redirect_codes = {301, 302, 303, 307, 308}
    remaining = 5

    while (
        remaining > 0
        and response.status_code in redirect_codes
        and response.headers.get('Location')
    ):
        remaining -= 1
        next_path = response.headers['Location']
        response = client.get(next_path, follow_redirects=False)
        hops.append((response.status_code, response.headers.get('Location')))

    return hops


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


def test_css_alias_resolves_without_user_specific_alias(client):
    missing_user = 'missing-css-user'

    default_response = client.get('/css/custom.css', follow_redirects=True)
    assert default_response.status_code == 200

    original_ensure = identity.ensure_css_alias_for_user

    def _maybe_ensure(user_id: str) -> bool:
        if user_id == missing_user:
            return False
        return original_ensure(user_id)

    _set_user_session(client, missing_user)
    with patch('identity.ensure_css_alias_for_user', side_effect=_maybe_ensure):
        missing_response = client.get('/css/custom.css', follow_redirects=True)

    assert missing_response.status_code == default_response.status_code
    assert missing_response.data == default_response.data


def test_css_alias_redirect_chain_is_consistent_with_session(client):
    default_chain = _collect_css_redirect_chain(client)
    assert default_chain
    assert default_chain[-1][0] == 200
    assert default_chain[-1][1] is None

    _set_user_session(client, 'alternate-user')
    alternate_chain = _collect_css_redirect_chain(client)
    assert alternate_chain == default_chain


def test_css_alias_outdated_definition_is_upgraded(client):
    with client.application.app_context():
        alias = get_alias_by_name('default-user', 'CSS')
        assert alias is not None
        alias.definition = 'css/custom.css -> /css/default\ncss/default -> /static/css/custom.css'
        db.session.add(alias)
        db.session.commit()

    response = client.get('/css/custom.css', follow_redirects=True)
    assert response.status_code == 200

    with client.application.app_context():
        refreshed = get_alias_by_name('default-user', 'CSS')
        assert refreshed is not None
        assert 'css/lightmode ->' in refreshed.definition
        assert 'css/darkmode ->' in refreshed.definition

    _set_user_session(client, 'alternate-user')
    alternate_response = client.get('/css/custom.css', follow_redirects=True)
    assert alternate_response.status_code == 200
