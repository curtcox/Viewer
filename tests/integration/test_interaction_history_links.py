"""Integration tests for interaction history timestamp links."""
from __future__ import annotations

import re

import pytest

from alias_definition import format_primary_alias_line
from database import db
from db_access import EntityInteractionRequest, record_entity_interaction
from models import Alias, Server, Variable
from models import Secret

pytestmark = pytest.mark.integration


def test_alias_edit_page_includes_history_links(client, integration_app):
    """Alias edit page should include links to /history and /server_events for each interaction timestamp."""
    
    with integration_app.app_context():
        alias = Alias(
            name="test-alias",
            definition=format_primary_alias_line(
                "literal",
                None,
                "/docs",
                alias_name="test-alias",
            ),
        )
        db.session.add(alias)
        db.session.commit()
        
        # Record an interaction
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type='alias',
                entity_name='test-alias',
                action='save',
                message='Initial creation',
                content='literal /docs',
            )
        )
    
    response = client.get("/aliases/test-alias/edit")
    assert response.status_code == 200
    
    page = response.get_data(as_text=True)
    
    # Check that the interaction history section exists
    assert "Recent edits and requests" in page
    
    # Check for links to /history with timestamp parameters
    history_link_pattern = r'href="/history\?start=[^"]+&end=[^"]+"'
    assert re.search(history_link_pattern, page), "Expected /history link with timestamp parameters"
    
    # Check for links to /server_events with timestamp parameters
    server_events_link_pattern = r'href="/server_events\?start=[^"]+&end=[^"]+"'
    assert re.search(server_events_link_pattern, page), "Expected /server_events link with timestamp parameters"


def test_server_edit_page_includes_history_links(client, integration_app):
    """Server edit page should include links to /history and /server_events for each interaction timestamp."""
    
    with integration_app.app_context():
        server = Server(
            name="test-server",
            definition="def handle(request):\n    return 'Hello'",
            enabled=True,
        )
        db.session.add(server)
        db.session.commit()
        
        # Record an interaction
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type='server',
                entity_name='test-server',
                action='save',
                message='Initial creation',
                content="def handle(request):\n    return 'Hello'",
            )
        )
    
    response = client.get("/servers/test-server/edit")
    assert response.status_code == 200
    
    page = response.get_data(as_text=True)
    
    # Check that the interaction history section exists
    assert "Recent edits and requests" in page
    
    # Check for links to /history with timestamp parameters
    history_link_pattern = r'href="/history\?start=[^"]+&end=[^"]+"'
    assert re.search(history_link_pattern, page), "Expected /history link with timestamp parameters"
    
    # Check for links to /server_events with timestamp parameters
    server_events_link_pattern = r'href="/server_events\?start=[^"]+&end=[^"]+"'
    assert re.search(server_events_link_pattern, page), "Expected /server_events link with timestamp parameters"


def test_variable_edit_page_includes_history_links(client, integration_app):
    """Variable edit page should include links to /history and /server_events for each interaction timestamp."""
    
    with integration_app.app_context():
        variable = Variable(
            name="test-variable",
            definition="test-value",
            enabled=True,
        )
        db.session.add(variable)
        db.session.commit()
        
        # Record an interaction
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type='variable',
                entity_name='test-variable',
                action='save',
                message='Initial creation',
                content='test-value',
            )
        )
    
    response = client.get("/variables/test-variable/edit")
    assert response.status_code == 200
    
    page = response.get_data(as_text=True)
    
    # Check that the interaction history section exists
    assert "Recent edits and requests" in page
    
    # Check for links to /history with timestamp parameters
    history_link_pattern = r'href="/history\?start=[^"]+&end=[^"]+"'
    assert re.search(history_link_pattern, page), "Expected /history link with timestamp parameters"
    
    # Check for links to /server_events with timestamp parameters
    server_events_link_pattern = r'href="/server_events\?start=[^"]+&end=[^"]+"'
    assert re.search(server_events_link_pattern, page), "Expected /server_events link with timestamp parameters"


def test_secret_edit_page_includes_history_links(client, integration_app):
    """Secret edit page should include links to /history and /server_events for each interaction timestamp."""
    
    with integration_app.app_context():
        secret = Secret(
            name="test-secret",
            definition="secret-value",
            enabled=True,
        )
        db.session.add(secret)
        db.session.commit()
        
        # Record an interaction
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type='secret',
                entity_name='test-secret',
                action='save',
                message='Initial creation',
                content='secret-value',
            )
        )
    
    response = client.get("/secrets/test-secret/edit")
    assert response.status_code == 200
    
    page = response.get_data(as_text=True)
    
    # Check that the interaction history section exists
    assert "Recent edits and requests" in page
    
    # Check for links to /history with timestamp parameters
    history_link_pattern = r'href="/history\?start=[^"]+&end=[^"]+"'
    assert re.search(history_link_pattern, page), "Expected /history link with timestamp parameters"
    
    # Check for links to /server_events with timestamp parameters
    server_events_link_pattern = r'href="/server_events\?start=[^"]+&end=[^"]+"'
    assert re.search(server_events_link_pattern, page), "Expected /server_events link with timestamp parameters"


def test_cid_edit_page_includes_history_links(client, integration_app):
    """CID edit page should include links to /history and /server_events for each interaction timestamp."""
    
    # Create some content to edit
    from cid_utils import generate_cid
    content = b"Test content for CID"
    cid = generate_cid(content)
    
    with integration_app.app_context():
        from db_access import create_cid_record
        create_cid_record(cid, content, 'text/plain')
        
        # Record an interaction
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type='cid',
                entity_name=cid,
                action='save',
                message='Content created',
                content='Test content for CID',
            )
        )
    
    response = client.get(f"/edit/{cid}")
    assert response.status_code == 200
    
    page = response.get_data(as_text=True)
    
    # Check that the interaction history section exists
    assert "Recent edits and requests" in page
    
    # Check for links to /history with timestamp parameters
    history_link_pattern = r'href="/history\?start=[^"]+&end=[^"]+"'
    assert re.search(history_link_pattern, page), "Expected /history link with timestamp parameters"
    
    # Check for links to /server_events with timestamp parameters
    server_events_link_pattern = r'href="/server_events\?start=[^"]+&end=[^"]+"'
    assert re.search(server_events_link_pattern, page), "Expected /server_events link with timestamp parameters"
