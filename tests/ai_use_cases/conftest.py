"""Pytest fixtures for AI use case evaluation tests."""

import json
import os
from datetime import datetime

import pytest

from server_execution.external_call_tracking import capture_external_calls, sanitize_external_calls


@pytest.fixture(scope="session")
def requires_openrouter_api_key():
    """Skip tests if OPENROUTER_API_KEY not available."""
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set - skipping AI evaluation tests")


@pytest.fixture(autouse=True)
def setup_ai_assist_server(memory_db_app):
    """Ensure ai_assist server is enabled and configured.

    This fixture runs automatically before each test to ensure the
    ai_assist server exists with proper configuration.
    """
    with memory_db_app.app_context():
        from database import db
        from models import Server, Variable, Secret

        # Create ai_assist server if not exists
        ai_server = db.session.query(Server).filter_by(name='ai_assist').first()
        if not ai_server:
            # Read the server definition from file
            definition_path = 'reference_templates/servers/definitions/ai_assist.py'
            with open(definition_path, encoding='utf-8') as f:
                definition = f.read()

            ai_server = Server(
                name='ai_assist',
                definition=definition,
                enabled=True
            )
            db.session.add(ai_server)

        # Ensure OPENROUTER_API_KEY secret exists
        api_key = os.getenv('OPENROUTER_API_KEY')
        if api_key:
            secret = db.session.query(Secret).filter_by(name='OPENROUTER_API_KEY').first()
            if not secret:
                secret = Secret(name='OPENROUTER_API_KEY', definition=api_key)
                db.session.add(secret)

        # Set default AI model variable
        ai_model = db.session.query(Variable).filter_by(name='AI_MODEL').first()
        if not ai_model:
            ai_model = Variable(
                name='AI_MODEL',
                definition=os.getenv('AI_MODEL', 'anthropic/claude-sonnet-4.5')
            )
            db.session.add(ai_model)

        # Set AI temperature variable
        ai_temp = db.session.query(Variable).filter_by(name='AI_TEMPERATURE').first()
        if not ai_temp:
            ai_temp = Variable(
                name='AI_TEMPERATURE',
                definition=os.getenv('AI_TEMPERATURE', '0.3')
            )
            db.session.add(ai_temp)

        # Set AI max tokens variable
        ai_tokens = db.session.query(Variable).filter_by(name='AI_MAX_TOKENS').first()
        if not ai_tokens:
            ai_tokens = Variable(
                name='AI_MAX_TOKENS',
                definition=os.getenv('AI_MAX_TOKENS', '4096')
            )
            db.session.add(ai_tokens)

        # Create /ai alias pointing to ai_assist
        from models import Alias
        ai_alias = db.session.query(Alias).filter_by(name='ai').first()
        if not ai_alias:
            ai_alias = Alias(
                name='ai',
                definition='ai -> /ai_assist',
                enabled=True
            )
            db.session.add(ai_alias)
        elif '/ai_stub' in (ai_alias.definition or ''):
            # Update existing alias to point to ai_assist
            ai_alias.definition = 'ai -> /ai_assist'

        db.session.commit()

    yield


class AIInteractionTracker:
    """Helper class to track AI interactions with external call capture."""

    def __init__(self):
        self.interactions = []
        self._secrets = {}
        self._pending_external_calls = []

    def set_secrets(self, secrets: dict):
        """Set the secrets dict for redaction of external calls."""
        self._secrets = secrets or {}

    def __call__(self, request_payload, response_data, status_code, external_calls=None):
        """Make the tracker callable for backwards compatibility.

        If external_calls is not provided, uses any pending calls from call_with_capture.
        """
        calls = external_calls if external_calls is not None else self._pending_external_calls
        self.record(request_payload, response_data, status_code, calls)
        self._pending_external_calls = []  # Clear pending calls after use

    def record(self, request_payload, response_data, status_code, external_calls=None):
        """Record an AI interaction with optional external calls."""
        self.interactions.append({
            'request': request_payload,
            'response': response_data,
            'status': status_code,
            'timestamp': datetime.utcnow().isoformat(),
            'external_calls': external_calls or []
        })

    def call_with_capture(self, client, method, url, **kwargs):
        """Make an HTTP request while capturing external calls.

        This wraps the client request and captures any outbound HTTP calls
        made during server execution (e.g., to OpenRouter API).

        The captured external calls are stored as pending and will be
        automatically associated with the next record() or __call__() invocation.

        Args:
            client: Flask test client
            method: HTTP method ('get', 'post', etc.)
            url: Request URL
            **kwargs: Additional arguments for the request

        Returns:
            tuple: (response, external_calls)
        """
        with capture_external_calls() as call_log:
            http_method = getattr(client, method.lower())
            response = http_method(url, **kwargs)

        # Sanitize external calls (redact secrets)
        external_calls = sanitize_external_calls(call_log, self._secrets)

        # Store as pending for auto-association with next record() call
        self._pending_external_calls = external_calls

        return response, external_calls


@pytest.fixture
def ai_interaction_tracker(request, memory_db_app):
    """Track AI interactions for debugging and analysis.

    This fixture records all AI requests and responses during a test.
    Interactions are saved to a JSON file for all tests (passed and failed).

    The tracker provides two ways to record interactions:
    1. tracker.record(payload, response, status) - manual recording
    2. tracker.call_with_capture(client, 'post', '/ai', json=payload) - auto-capture external calls
    """
    tracker = AIInteractionTracker()

    # Get secrets for redaction
    with memory_db_app.app_context():
        from models import Secret
        from database import db
        secrets = {s.name: s.definition for s in db.session.query(Secret).all()}
        tracker.set_secrets(secrets)

    yield tracker

    # Save interactions for all tests (not just failures)
    test_name = request.node.name
    test_file = request.node.fspath.basename
    test_module = request.node.module.__name__
    test_doc = request.node.function.__doc__ or ""

    # Determine test status - handle passed, failed, and other states (e.g., skipped)
    passed = hasattr(request.node, 'rep_call') and getattr(request.node.rep_call, 'passed', False)
    failed = hasattr(request.node, 'rep_call') and getattr(request.node.rep_call, 'failed', False)

    output_dir = 'test-results/ai-interactions'
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f'{test_name}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_name': test_name,
            'test_file': test_file,
            'test_module': test_module,
            'test_doc': test_doc.strip(),
            'test_file_path': str(request.node.fspath),
            'passed': passed,
            'failed': failed,
            'interactions': tracker.interactions
        }, f, indent=2)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for interaction tracker."""
    outcome = yield
    rep = outcome.get_result()

    # Store result in the item for access by fixtures
    setattr(item, f"rep_{rep.when}", rep)
