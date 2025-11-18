"""Integration tests ensuring alias and server responses ignore user identity."""
from __future__ import annotations

from typing import Optional

from unittest.mock import patch

import pytest

from database import db
from db_access import get_alias_by_name, get_server_by_name
from identity import ensure_default_resources


@pytest.fixture(autouse=True)
def _ensure_default_resources(client):
    """Ensure default global resources exist for every test."""

    with client.application.app_context():
        ensure_default_resources()


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

    default_alias = get_alias_by_name(alias_name)
    assert default_alias is not None

    response_repeat = client.post('/aliases/new', data=payload, follow_redirects=False)
    assert response_repeat.status_code == 200

    repeat_alias = get_alias_by_name(alias_name)
    assert repeat_alias is not None
    assert repeat_alias.definition == default_alias.definition


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

    default_server = get_server_by_name(server_name)
    assert default_server is not None

    response_repeat = client.post('/servers/new', data=payload, follow_redirects=False)
    assert response_repeat.status_code == 200

    repeat_server = get_server_by_name(server_name)
    assert repeat_server is not None
    assert repeat_server.definition == default_server.definition


def test_css_alias_resolves_without_user_specific_alias(client):
    default_response = client.get('/css/custom.css', follow_redirects=True)
    assert default_response.status_code == 200

    def _maybe_ensure() -> bool:
        return False

    # Delete CSS alias to simulate it being missing
    with client.application.app_context():
        alias = get_alias_by_name('CSS')
        if alias:
            db.session.delete(alias)
            db.session.commit()

    with patch('identity.ensure_css_alias', side_effect=_maybe_ensure):
        missing_response = client.get('/css/custom.css', follow_redirects=False)

    assert missing_response.status_code == 404


def test_css_alias_redirect_chain_is_consistent_with_session(client):
    default_chain = _collect_css_redirect_chain(client)
    assert default_chain
    assert default_chain[-1][0] == 200
    assert default_chain[-1][1] is None

    repeat_chain = _collect_css_redirect_chain(client)
    assert repeat_chain == default_chain


def test_css_alias_outdated_definition_is_upgraded(client):
    with client.application.app_context():
        alias = get_alias_by_name('CSS')
        assert alias is not None
        alias.definition = 'css/custom.css -> /css/default\ncss/default -> /static/css/custom.css'
        db.session.add(alias)
        db.session.commit()

    response = client.get('/css/custom.css', follow_redirects=True)
    assert response.status_code == 200

    with client.application.app_context():
        refreshed = get_alias_by_name('CSS')
        assert refreshed is not None
        assert 'css/lightmode ->' in refreshed.definition
        assert 'css/darkmode ->' in refreshed.definition

    repeat_response = client.get('/css/custom.css', follow_redirects=True)
    assert repeat_response.status_code == 200
