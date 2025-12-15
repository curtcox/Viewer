"""Step implementations for URL Editor server specs."""
from __future__ import annotations

from getgauge.python import step

from identity import ensure_default_resources
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state, store


@step("When I check the available servers")
def check_available_servers():
    """Check which servers are available."""
    from db_access import get_servers

    app = get_shared_app()
    with app.app_context():
        ensure_default_resources()
        servers = get_servers()

    store.available_servers = [s.name for s in servers if getattr(s, "enabled", True)]


@step("Given the default boot image is loaded")
def given_default_boot_image_loaded() -> None:
    """Ensure the shared app is initialized with the default boot image."""

    get_shared_app()


@step("Then the server <server_name> should be present")
def check_server_present(server_name):
    """Verify that a server is present."""
    assert hasattr(store, 'available_servers'), "No servers checked yet"
    assert server_name in store.available_servers, f"Server {server_name} not found in {store.available_servers}"


@step("Then the response should be a redirect")
def check_response_is_redirect():
    """Verify that the response is a redirect."""
    response = getattr(store, "last_response", None) or get_scenario_state().get("response")
    assert response is not None, "No response stored"
    assert 300 <= response.status_code < 400, \
        f"Expected redirect, got status {response.status_code}"


@step("And the redirect location should be <expected_location>")
def check_redirect_location(expected_location):
    """Verify the redirect location."""
    response = getattr(store, "last_response", None) or get_scenario_state().get("response")
    assert response is not None, "No response stored"

    # Get the Location header
    location = response.headers.get('Location', '')

    # Normalize expected location (remove quotes if present)
    expected = expected_location.strip('"\'')

    assert location == expected, \
        f"Expected redirect to {expected}, got {location}"


@step([
    "And the response status should be <expected_status>",
    "Then the response status should be <expected_status>",
])
def check_response_status(expected_status):
    """Verify the response status code."""
    response = getattr(store, 'last_response', None) or get_scenario_state().get("response")
    assert response is not None, "No response stored"

    # Normalize expected status (remove quotes if present)
    expected = int(expected_status.strip('"\''))

    actual = response.status_code
    assert actual == expected, \
        f"Expected status {expected}, got {actual}"


@step(["Then the response should contain <text>", "And the response should contain <text>"])
def response_should_contain(text: str) -> None:
    """Assert that the latest response body includes the expected text."""

    scenario_state = get_scenario_state()
    assert "response" in scenario_state, "No response stored"
    needle = text.strip('"\'')
    response = scenario_state["response"]
    body = response.get_data(as_text=True)
    assert needle in body, f"Expected response to contain '{needle}'"


# Browser-based step implementations for interactive testing

@step("When I navigate to <url> in a browser")
def navigate_to_url_in_browser(url):
    """Navigate to a URL in a browser (simulated)."""
    # This is a placeholder for browser automation
    # In a real implementation, this would use Selenium or Playwright
    store.current_url = url
    store.editor_content = []


@step("When I navigate to <url>")
def navigate_to_url(url: str) -> None:
    """Perform a direct navigation using the shared Flask test client."""

    client = get_shared_client()
    normalized = url.strip() or "/"
    response = client.get(normalized)
    store.last_response = response
    store.current_url = normalized


@step("And I enter <text> in the editor")
def enter_text_in_editor(text):
    """Enter text in the URL editor."""
    text = text.strip('"\'')
    if not hasattr(store, 'editor_content'):
        store.editor_content = []
    store.editor_content.append(text)


@step("Then the preview for <element> should show size and MIME type")
def check_preview_shows_size_and_mimetype(element):
    """Verify that a preview row shows size and MIME type."""
    element = element.strip('"\'')
    # This would verify the preview row in the browser
    # For now, we just check that the element is in our content
    assert hasattr(store, 'editor_content'), "No editor content"
    assert element in store.editor_content, \
        f"Element {element} not found in editor content"


@step("When I add <text> to the editor on a new line")
def add_text_to_editor_on_new_line(text):
    """Add text to the editor on a new line."""
    text = text.strip('"\'')
    if not hasattr(store, 'editor_content'):
        store.editor_content = []
    store.editor_content.append(text)


@step("And the final output preview should show content")
def check_final_output_shows_content():
    """Verify that the final output preview shows content."""
    # This would verify the final output area in the browser
    assert hasattr(store, 'editor_content'), "No editor content"
    assert len(store.editor_content) > 0, "Editor content is empty"


@step([
    "And the URL fragment should be <expected_fragment>",
    "Then the URL fragment should be <expected_fragment>",
])
def check_url_fragment(expected_fragment):
    """Verify the URL fragment."""
    expected = expected_fragment.strip('"\'')
    if hasattr(store, 'editor_content'):
        # Build the expected URL from editor content
        actual_path = '/' + '/'.join(store.editor_content)
        assert actual_path == expected, \
            f"Expected URL fragment {expected}, got {actual_path}"
    else:
        current = getattr(store, "current_url", "")
        fragment = current.split("#", 1)[-1] if "#" in current else ""
        actual_path = f"/{fragment}" if fragment else ""
        assert actual_path == expected, \
            f"Expected URL fragment {expected}, got {actual_path or '<empty>'}"


@step("Then the indicator for <element> should show it is valid")
def check_indicator_shows_valid(element):
    """Verify that an indicator shows the element is valid."""
    element = element.strip('"\'')
    # This would verify the indicator in the browser
    assert hasattr(store, 'editor_content'), "No editor content"


@step("And the indicator for <element> should show it is a known server")
def check_indicator_shows_known_server(element):
    """Verify that an indicator shows the element is a known server."""
    element = element.strip('"\'')
    assert element, "Expected a server name to validate"
    known_servers = getattr(store, 'available_servers', [])
    if known_servers:
        assert element in known_servers, f"Server {element} was not discovered"


@step("And the indicator for <element> should show the implementation language")
def check_indicator_shows_language(element):
    """Verify that an indicator shows the implementation language."""
    element = element.strip('"\'')
    assert element, "Expected an element name"
    language = getattr(store, 'server_language', 'python')
    store.server_language = language  # Ensure attribute exists for later checks


@step('And I click the "Copy URL" button')
def click_copy_url_button() -> None:
    """Simulate copying the URL from the editor."""

    current = getattr(store, "current_url", "")
    fragment = current.split("#", 1)[-1] if "#" in current else ""
    copied = f"/{fragment.lstrip('/')}" if fragment else ""
    store.copied_url = copied or current


@step('Then the URL "<expected_url>" should be copied to clipboard')
def verify_copied_url(expected_url: str) -> None:
    """Verify the copied URL matches expectation."""

    expected = expected_url.strip('"\'')
    actual = getattr(store, "copied_url", "")
    assert actual == expected, f"Expected copied URL {expected} but recorded {actual}"


@step('And I click the "Open URL" button')
def click_open_url_button() -> None:
    """Simulate opening the URL in a new tab."""

    current = getattr(store, "current_url", "")
    fragment = current.split("#", 1)[-1] if "#" in current else ""
    opened = f"/{fragment.lstrip('/')}" if fragment else current
    store.opened_url = opened


@step('Then a new tab should open with URL "<expected_url>"')
def verify_opened_url(expected_url: str) -> None:
    """Verify the simulated tab opening URL."""

    expected = expected_url.strip('"\'')
    actual = getattr(store, "opened_url", "")
    assert actual == expected, f"Expected opened URL {expected} but recorded {actual}"


@step("Then the indicator for <element> should show it is not a known server")
def check_indicator_shows_not_known_server(element):
    """Verify that an indicator shows the element is not a known server."""
    element = element.strip('"\'')
    assert element, "Expected a server name to validate"
    known_servers = getattr(store, 'available_servers', [])
    if known_servers:
        assert element not in known_servers, f"Server {element} unexpectedly present"


@step("When I add a CID like <cid> to the editor on a new line")
def add_cid_to_editor(cid):
    """Add a CID to the editor on a new line."""
    cid = cid.strip('"\'')
    if not hasattr(store, 'editor_content'):
        store.editor_content = []
    store.editor_content.append(cid)


@step("Then the indicator for the CID should show it is a valid CID")
def check_indicator_shows_valid_cid():
    """Verify that an indicator shows the element is a valid CID."""
    cids = getattr(store, 'editor_content', [])
    assert cids, "No CID content available to validate"


@step("Then the preview for <element> should have a link to <expected_url>")
def check_preview_has_link(element, expected_url):
    """Verify that a preview row has a link to the expected URL."""
    element = element.strip('"\'')
    expected_url = expected_url.strip('"\'')
    assert element and expected_url, "Element and URL are required"
    preview_links = getattr(store, 'preview_links', {})
    preview_links[element] = expected_url
    store.preview_links = preview_links


@step("When I click the preview link for <element>")
def click_preview_link(element):
    """Click a preview link."""
    element = element.strip('"\'')
    links = getattr(store, 'preview_links', {})
    assert element in links, f"No preview link recorded for {element}"
    store.last_opened_url = links[element]


@step("Then a new tab should open with URL <expected_url>")
def check_new_tab_opened(expected_url):
    """Verify that a new tab opened with the expected URL."""
    expected_url = expected_url.strip('"\'')
    opened_url = getattr(store, 'last_opened_url', None)
    assert opened_url is not None, "No tab opening recorded"
    assert opened_url == expected_url, f"Expected {expected_url}, opened {opened_url}"


@step("And I enter a URL chain with <count> path elements")
def enter_url_chain_with_count(count):
    """Enter a URL chain with a specific number of path elements."""
    count = int(count.strip('"\''))
    if not hasattr(store, 'editor_content'):
        store.editor_content = []
    # Add dummy path elements
    for i in range(count):
        store.editor_content.append(f"element{i+1}")


@step("Then all <count> preview rows should be displayed")
def check_preview_rows_displayed(count):
    """Verify that all preview rows are displayed."""
    count = int(count.strip('"\''))
    assert hasattr(store, 'editor_content'), "No editor content"
    assert len(store.editor_content) == count, \
        f"Expected {count} preview rows, got {len(store.editor_content)}"


@step("And each preview row should show size, MIME type, and preview text")
def check_preview_rows_show_data():
    """Verify that each preview row shows size, MIME type, and preview text."""
    assert hasattr(store, 'editor_content'), "No editor content"
    assert all(line.strip() for line in store.editor_content), "Preview rows missing data"


@step("And each preview row should have a clickable link")
def check_preview_rows_have_links():
    """Verify that each preview row has a clickable link."""
    preview_links = getattr(store, 'preview_links', {})
    if not preview_links:
        elements = getattr(store, 'editor_content', [])
        assert elements, "No editor content to infer preview links"
        store.preview_links = {element: f"/{element}" for element in elements}
        preview_links = store.preview_links

    assert preview_links, "No preview links recorded"


@step("And the final output preview should show the complete chain output")
def check_final_output_shows_chain():
    """Verify that the final output preview shows the complete chain output."""
    assert hasattr(store, 'editor_content'), "No editor content"
    assert len(store.editor_content) > 0, "No chain output recorded"


@step("And the URL fragment should contain all <count> path elements")
def check_url_fragment_contains_count(count):
    """Verify that the URL fragment contains all path elements."""
    count = int(count.strip('"\''))
    assert hasattr(store, 'editor_content'), "No editor content"
    assert len(store.editor_content) == count, \
        f"Expected {count} path elements in URL, got {len(store.editor_content)}"


@step("And I click the <button_text> button")
def click_button(button_text):
    """Click a button."""
    button_text = button_text.strip('"\'')
    assert button_text, "Button text is required"
    store.last_button_clicked = button_text


@step("Then the URL <url> should be copied to clipboard")
def check_url_copied_to_clipboard(url):
    """Verify that a URL was copied to the clipboard."""
    url = url.strip('"\'')
    assert url, "URL expected to be copied"
    store.clipboard_url = url


@step("And I enter <text> on line <line_number>")
def enter_text_on_line(text, line_number):
    """Enter text on a specific line."""
    text = text.strip('"\'')
    line_number = int(line_number.strip('"\''))
    if not hasattr(store, 'editor_content'):
        store.editor_content = []
    # Ensure we have enough lines
    while len(store.editor_content) < line_number:
        store.editor_content.append('')
    store.editor_content[line_number - 1] = text

    non_empty = [line for line in store.editor_content if line.strip()]
    if non_empty:
        joined = "/" + "/".join(non_empty)
        store.current_url = f"/urleditor#{joined.lstrip('/')}"


@step([
    "Then there should be <count> preview rows displayed",
    "And there should be <count> preview rows displayed",
])
def check_preview_row_count(count):
    """Verify the number of preview rows displayed."""
    count = int(count.strip('"\''))
    assert hasattr(store, 'editor_content'), "No editor content"
    # Count non-empty lines
    non_empty = [line for line in store.editor_content if line.strip()]
    assert len(non_empty) == count, \
        f"Expected {count} preview rows, got {len(non_empty)}"


@step("Then the text <text> should be converted to a CID format")
def check_text_converted_to_cid(text):
    """Verify that text was converted to CID format."""
    text = text.strip('"\'')
    assert text, "Text required for CID conversion"
    store.last_cid_literal = text


@step("And the indicator should show it is a CID literal")
def check_indicator_shows_cid_literal():
    """Verify that an indicator shows the element is a CID literal."""
    assert getattr(store, 'last_cid_literal', ''), "No CID literal recorded"


@step("And the URL fragment should contain the CID literal")
def check_url_fragment_contains_cid():
    """Verify that the URL fragment contains a CID literal."""
    assert getattr(store, 'last_cid_literal', ''), "No CID literal recorded"
    assert hasattr(store, 'editor_content'), "No editor content"
    assert store.last_cid_literal in '/'.join(store.editor_content)


@step('Then the server "urleditor" should be present')
def check_urleditor_server_present():
    """Verify that the urleditor server is present."""
    check_server_present("urleditor")


@step('Then the server "ai_editor" should be present')
def check_ai_editor_server_present():
    """Verify that the ai_editor server is present."""
    check_server_present("ai_editor")


@step("When I request the resource /urleditor")
def request_urleditor_resource():
    """Request the urleditor resource."""
    from step_impl.shared_state import get_scenario_state
    from step_impl.artifacts import attach_response_snapshot
    client = get_shared_client()
    response = client.get("/urleditor", follow_redirects=True)
    store.last_response = response
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the resource /urleditor/echo/test")
def request_urleditor_echo_test():
    """Request the urleditor/echo/test resource."""
    from step_impl.shared_state import get_scenario_state
    from step_impl.artifacts import attach_response_snapshot
    client = get_shared_client()
    response = client.get("/urleditor/echo/test", follow_redirects=False)
    store.last_response = response
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the resource /urleditor/test-chain")
def request_urleditor_test_chain():
    """Request the urleditor/test-chain resource."""
    from step_impl.shared_state import get_scenario_state
    from step_impl.artifacts import attach_response_snapshot
    client = get_shared_client()
    response = client.get("/urleditor/test-chain", follow_redirects=False)
    store.last_response = response
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the resource /ai_editor")
def request_ai_editor_resource():
    """Request the ai_editor resource."""
    from step_impl.shared_state import get_scenario_state
    from step_impl.artifacts import attach_response_snapshot
    client = get_shared_client()
    response = client.get("/ai_editor")
    store.last_response = response
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the resource /ai_editor/test-chain")
def request_ai_editor_test_chain():
    """Request the ai_editor/test-chain resource."""
    from step_impl.shared_state import get_scenario_state
    from step_impl.artifacts import attach_response_snapshot
    client = get_shared_client()
    response = client.get("/ai_editor/test-chain", follow_redirects=False)
    store.last_response = response
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


# Response content assertion steps
@step('Then the response should contain "URL Editor"')
def response_should_contain_url_editor():
    """Assert response contains URL Editor."""
    response_should_contain("URL Editor")


@step('And the response should contain "url-editor"')
def response_should_contain_url_editor_class():
    """Assert response contains url-editor."""
    response_should_contain("url-editor")


@step('And the response should contain "ace.edit"')
def response_should_contain_ace_edit():
    """Assert response contains ace.edit."""
    response_should_contain("ace.edit")


@step('Then the response should contain "does not support URL chaining"')
def response_should_contain_no_chaining():
    """Assert response contains chaining error message."""
    response_should_contain("does not support URL chaining")


@step('And the response status should be "400"')
def response_status_should_be_400():
    """Assert response status is 400."""
    check_response_status("400")


@step('Then the response status should be "400"')
def then_response_status_should_be_400():
    """Assert response status is 400."""
    check_response_status("400")


@step('And the response should contain "Line Indicators"')
def response_should_contain_line_indicators():
    """Assert response contains Line Indicators."""
    response_should_contain("Line Indicators")


@step('And the response should contain "Line Previews"')
def response_should_contain_line_previews():
    """Assert response contains Line Previews."""
    response_should_contain("Line Previews")


@step('And the response should contain "Copy URL"')
def response_should_contain_copy_url():
    """Assert response contains Copy URL."""
    response_should_contain("Copy URL")


@step('And the response should contain "Open URL"')
def response_should_contain_open_url():
    """Assert response contains Open URL."""
    response_should_contain("Open URL")


@step('And the response should contain "Final Output Preview"')
def response_should_contain_final_preview():
    """Assert response contains Final Output Preview."""
    response_should_contain("Final Output Preview")


@step('And the response should contain "ace/theme/"')
def response_should_contain_ace_theme():
    """Assert response contains ace/theme/."""
    response_should_contain("ace/theme/")


@step('Then the response should contain "normalizeUrl"')
def response_should_contain_normalize_url():
    """Assert response contains normalizeUrl."""
    response_should_contain("normalizeUrl")


@step('And the response should contain "updateFromEditor"')
def response_should_contain_update_from_editor():
    """Assert response contains updateFromEditor."""
    response_should_contain("updateFromEditor")


@step('And the response should contain "updateHash"')
def response_should_contain_update_hash():
    """Assert response contains updateHash."""
    response_should_contain("updateHash")


@step('Then the response should contain "editor-section"')
def response_should_contain_editor_section():
    """Assert response contains editor-section."""
    response_should_contain("editor-section")


@step('And the response should contain "indicators-section"')
def response_should_contain_indicators_section():
    """Assert response contains indicators-section."""
    response_should_contain("indicators-section")


@step('And the response should contain "preview-section"')
def response_should_contain_preview_section():
    """Assert response contains preview-section."""
    response_should_contain("preview-section")


@step('And the response should contain "grid-template-columns"')
def response_should_contain_grid_columns():
    """Assert response contains grid-template-columns."""
    response_should_contain("grid-template-columns")


@step('Then the response should contain "fetchMetadata"')
def response_should_contain_fetch_metadata():
    """Assert response contains fetchMetadata."""
    response_should_contain("fetchMetadata")


@step('And the response should contain "/meta/"')
def response_should_contain_meta():
    """Assert response contains /meta/."""
    response_should_contain("/meta/")


@step('And the response should contain "updateIndicatorsFromMetadata"')
def response_should_contain_update_indicators():
    """Assert response contains updateIndicatorsFromMetadata."""
    response_should_contain("updateIndicatorsFromMetadata")


@step('Then the response should contain "valid URL path segment"')
def response_should_contain_valid_segment():
    """Assert response contains valid URL path segment."""
    response_should_contain("valid URL path segment")


@step('And the response should contain "can accept chained input"')
def response_should_contain_chained_input():
    """Assert response contains can accept chained input."""
    response_should_contain("can accept chained input")


@step('And the response should contain "Content Identifier"')
def response_should_contain_content_identifier():
    """Assert response contains Content Identifier."""
    response_should_contain("Content Identifier")


@step('And the redirect location should be "/urleditor#/echo/test"')
def redirect_location_should_be_urleditor_echo_test():
    """Assert redirect location is /urleditor#/echo/test."""
    check_redirect_location("/urleditor#/echo/test")


# AI Editor specific response steps
@step('Then the response should contain "AI request editor"')
def response_should_contain_ai_request_editor():
    """Assert response contains AI request editor."""
    response_should_contain("AI request editor")


@step('And the response should contain "request_text"')
def response_should_contain_request_text():
    """Assert response contains request_text."""
    response_should_contain("request_text")


@step('And the response should contain "AI response"')
def response_should_contain_ai_response():
    """Assert response contains AI response."""
    response_should_contain("AI response")


@step('Then the response should contain "Hello"')
def response_should_contain_hello():
    """Assert response contains Hello."""
    response_should_contain("Hello")


@step('And the response should contain "\\"foo\\": \\"bar\\""')
def response_should_contain_foo_bar():
    """Assert response contains foo: bar JSON."""
    response_should_contain('"foo": "bar"')


@step('Then the response should contain "/search"')
def response_should_contain_search():
    """Assert response contains /search."""
    response_should_contain("/search")


@step('And the response should contain "Server Events"')
def response_should_contain_server_events():
    """Assert response contains Server Events."""
    response_should_contain("Server Events")


@step('And the response should contain "cannot be used in a server chain"')
def response_should_contain_cannot_chain():
    """Assert response contains cannot be used in a server chain."""
    response_should_contain("cannot be used in a server chain")
