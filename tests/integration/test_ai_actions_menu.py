import pytest

pytestmark = pytest.mark.integration


def test_upload_page_includes_ai_action_menu(client, integration_app):
    """AI action controls should expose the menu links on upload page."""

    response = client.get('/upload')
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert 'data-ai-request-editor' in page
    assert '/aliases/ai' in page
    assert '/servers/ai_stub' in page
    assert '/ai_about' in page
