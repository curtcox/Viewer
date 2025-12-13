"""Tests for AI evaluation report generation and external call capture.

These tests validate that:
1. AIInteractionTracker captures external HTTP calls during requests
2. External calls are properly redacted (secrets replaced)
3. HTML report generator formats external calls correctly
4. JSON interaction files include external_calls data
"""

import json

import requests

from server_execution.external_call_tracking import capture_external_calls, sanitize_external_calls


class TestAIInteractionTracker:
    """Tests for the AIInteractionTracker class from conftest."""

    def test_tracker_records_interactions(self):
        """Test that tracker records basic interactions."""
        # Import the class directly to test it
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()

        payload = {'request_text': 'test', 'original_text': 'original'}
        response = {'updated_text': 'modified'}

        tracker.record(payload, response, 200)

        assert len(tracker.interactions) == 1
        assert tracker.interactions[0]['request'] == payload
        assert tracker.interactions[0]['response'] == response
        assert tracker.interactions[0]['status'] == 200
        assert 'timestamp' in tracker.interactions[0]
        assert tracker.interactions[0]['external_calls'] == []

    def test_tracker_records_external_calls(self):
        """Test that tracker includes external calls when provided."""
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()

        external_calls = [{
            'request': {
                'method': 'POST',
                'url': 'https://openrouter.ai/api/v1/chat/completions',
                'headers': {'Authorization': 'Bearer <secret:OPENROUTER_API_KEY>'},
                'json': {'model': 'test-model'}
            },
            'response': {
                'status_code': 200,
                'body': '{"choices": []}'
            }
        }]

        tracker.record({'test': 'payload'}, {'test': 'response'}, 200, external_calls)

        assert len(tracker.interactions) == 1
        assert len(tracker.interactions[0]['external_calls']) == 1
        assert tracker.interactions[0]['external_calls'][0]['request']['method'] == 'POST'

    def test_tracker_callable_uses_pending_calls(self):
        """Test that __call__ uses pending external calls from call_with_capture."""
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()

        # Simulate pending calls (as would be set by call_with_capture)
        pending_calls = [{'request': {'method': 'GET', 'url': 'http://test.com'}, 'response': {}}]
        tracker._pending_external_calls = pending_calls

        # Call tracker without explicit external_calls
        tracker({'test': 'payload'}, {'test': 'response'}, 200)

        assert len(tracker.interactions) == 1
        assert len(tracker.interactions[0]['external_calls']) == 1
        assert tracker._pending_external_calls == []  # Should be cleared

    def test_tracker_callable_clears_pending_after_use(self):
        """Test that pending calls are cleared after being used."""
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()
        tracker._pending_external_calls = [{'test': 'call'}]

        tracker({'test': 'payload'}, {'test': 'response'}, 200)

        assert tracker._pending_external_calls == []

    def test_tracker_secrets_redaction(self):
        """Test that secrets are set for redaction."""
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()
        secrets = {'API_KEY': 'secret-value-123'}
        tracker.set_secrets(secrets)

        assert tracker._secrets == secrets


class TestExternalCallCapture:
    """Tests for external call capture during HTTP requests."""

    def test_capture_external_calls_basic(self, monkeypatch):
        """Test basic external call capture."""
        def fake_request(self, method, url, **kwargs):
            response = requests.Response()
            response.status_code = 200
            response._content = b'{"result": "ok"}'
            response.headers = {'Content-Type': 'application/json'}
            response.url = url
            return response

        monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

        with capture_external_calls() as call_log:
            session = requests.Session()
            session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"model": "test"},
                headers={"Authorization": "Bearer test-key"}
            )

        assert len(call_log) == 1
        assert call_log[0]['request']['method'] == 'POST'
        assert 'openrouter.ai' in call_log[0]['request']['url']
        assert call_log[0]['response']['status_code'] == 200

    def test_sanitize_redacts_api_key(self, monkeypatch):
        """Test that API keys are properly redacted."""
        secret_key = "sk-or-v1-abc123xyz789"

        def fake_request(self, method, url, **kwargs):
            response = requests.Response()
            response.status_code = 200
            response._content = b'{"result": "ok"}'
            response.headers = {}
            response.url = url
            return response

        monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

        with capture_external_calls() as call_log:
            session = requests.Session()
            session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {secret_key}"}
            )

        sanitized = sanitize_external_calls(call_log, {"OPENROUTER_API_KEY": secret_key})

        # API key should be redacted
        auth_header = sanitized[0]['request']['headers'].get('Authorization', '')
        assert secret_key not in auth_header
        assert '<secret:OPENROUTER_API_KEY>' in auth_header


class TestReportGeneration:
    """Tests for HTML report generation with external calls."""

    def test_format_external_call_html_basic(self):
        """Test formatting of a basic external API call."""
        from scripts.generate_ai_eval_reports import format_external_call_html

        call = {
            'request': {
                'method': 'POST',
                'url': 'https://openrouter.ai/api/v1/chat/completions',
                'headers': {'Authorization': 'Bearer <secret:OPENROUTER_API_KEY>'},
                'json': {'model': 'anthropic/claude-sonnet-4.5', 'messages': []},
                'timeout': 60
            },
            'response': {
                'status_code': 200,
                'headers': {'content-type': 'application/json'},
                'body': '{"choices": [{"message": {"content": "Hello!"}}]}'
            }
        }

        html = format_external_call_html(call, 1)

        # Check that key elements are present
        assert 'API Call 1' in html
        assert 'POST' in html
        assert 'openrouter.ai' in html
        assert '<secret:OPENROUTER_API_KEY>' in html
        assert 'Status:' in html
        assert '200' in html

    def test_format_external_call_html_redacted_key(self):
        """Test that redacted API keys appear correctly in HTML."""
        from scripts.generate_ai_eval_reports import format_external_call_html

        call = {
            'request': {
                'method': 'POST',
                'url': 'https://openrouter.ai/api/v1/chat/completions',
                'headers': {'Authorization': 'Bearer <secret:OPENROUTER_API_KEY>'},
                'json': {}
            },
            'response': {
                'status_code': 200,
                'body': '{}'
            }
        }

        html = format_external_call_html(call, 1)

        # Verify the redacted secret name appears, not an actual key
        assert '<secret:OPENROUTER_API_KEY>' in html
        # Should not contain actual API key patterns
        assert 'sk-or-' not in html

    def test_format_external_calls_section_empty(self):
        """Test that empty external calls returns empty string."""
        from scripts.generate_ai_eval_reports import format_external_calls_section

        result = format_external_calls_section([])
        assert result == ''

        result = format_external_calls_section(None)
        assert result == ''

    def test_format_external_calls_section_with_calls(self):
        """Test formatting multiple external calls."""
        from scripts.generate_ai_eval_reports import format_external_calls_section

        calls = [
            {
                'request': {'method': 'POST', 'url': 'https://api1.com'},
                'response': {'status_code': 200, 'body': '{}'}
            },
            {
                'request': {'method': 'GET', 'url': 'https://api2.com'},
                'response': {'status_code': 201, 'body': '{}'}
            }
        ]

        html = format_external_calls_section(calls)

        assert 'OpenRouter API Details' in html
        assert 'API Call 1' in html
        assert 'API Call 2' in html

    def test_format_external_call_error_status(self):
        """Test formatting of error status codes."""
        from scripts.generate_ai_eval_reports import format_external_call_html

        call = {
            'request': {'method': 'POST', 'url': 'https://api.example.com'},
            'response': {'status_code': 401, 'body': '{"error": "unauthorized"}'}
        }

        html = format_external_call_html(call, 1)

        assert '401' in html
        assert 'api-status-error' in html


class TestInteractionJSONOutput:
    """Tests for JSON interaction file output format."""

    def test_interaction_json_includes_external_calls(self, tmp_path):
        """Test that saved JSON includes external_calls field."""
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()

        external_calls = [{
            'request': {
                'method': 'POST',
                'url': 'https://openrouter.ai/api/v1/chat/completions',
                'headers': {'Authorization': 'Bearer <secret:OPENROUTER_API_KEY>'},
                'json': {'model': 'test'}
            },
            'response': {
                'status_code': 200,
                'body': '{"choices": []}'
            }
        }]

        tracker.record(
            {'request_text': 'test'},
            {'updated_text': 'result'},
            200,
            external_calls
        )

        # Simulate saving to JSON (as done in the fixture)
        output_file = tmp_path / 'test_interaction.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_name': 'test_example',
                'interactions': tracker.interactions
            }, f, indent=2)

        # Read back and verify
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'interactions' in data
        assert len(data['interactions']) == 1
        assert 'external_calls' in data['interactions'][0]
        assert len(data['interactions'][0]['external_calls']) == 1
        assert data['interactions'][0]['external_calls'][0]['request']['method'] == 'POST'

    def test_interaction_json_serializable(self):
        """Test that interaction data is JSON serializable."""
        from tests.ai_use_cases.conftest import AIInteractionTracker

        tracker = AIInteractionTracker()

        # Add complex data that should be JSON serializable
        tracker.record(
            {'nested': {'data': [1, 2, 3]}, 'unicode': 'Hello 世界'},
            {'result': True, 'items': ['a', 'b']},
            200,
            [{'request': {'headers': {'X-Custom': 'value'}}, 'response': {'status_code': 200}}]
        )

        # Should not raise
        json_str = json.dumps(tracker.interactions)
        assert json_str is not None

        # Round-trip should preserve data
        parsed = json.loads(json_str)
        assert parsed[0]['request']['unicode'] == 'Hello 世界'


class TestHighlightJson:
    """Tests for JSON syntax highlighting."""

    def test_highlight_json_basic(self):
        """Test basic JSON highlighting."""
        from scripts.generate_ai_eval_reports import highlight_json

        data = {"key": "value", "number": 42}
        html = highlight_json(data)

        # Should contain the data
        assert 'key' in html
        assert 'value' in html
        assert '42' in html

    def test_highlight_json_handles_non_serializable(self):
        """Test that non-serializable data falls back gracefully."""
        from scripts.generate_ai_eval_reports import highlight_json

        class NonSerializable:
            def __str__(self):
                return "custom-object"

        result = highlight_json(NonSerializable())

        # Should fall back to escaped string representation
        assert 'custom-object' in result
