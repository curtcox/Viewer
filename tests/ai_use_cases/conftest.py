"""Pytest fixtures for AI use case evaluation tests."""

import json
import os
from datetime import datetime

import pytest


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
            with open(definition_path) as f:
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
                secret = Secret(name='OPENROUTER_API_KEY', value=api_key)
                db.session.add(secret)

        # Set default AI model variable
        ai_model = db.session.query(Variable).filter_by(name='AI_MODEL').first()
        if not ai_model:
            ai_model = Variable(
                name='AI_MODEL',
                value=os.getenv('AI_MODEL', 'anthropic/claude-sonnet-4-20250514')
            )
            db.session.add(ai_model)

        # Set AI temperature variable
        ai_temp = db.session.query(Variable).filter_by(name='AI_TEMPERATURE').first()
        if not ai_temp:
            ai_temp = Variable(
                name='AI_TEMPERATURE',
                value=os.getenv('AI_TEMPERATURE', '0.3')
            )
            db.session.add(ai_temp)

        # Set AI max tokens variable
        ai_tokens = db.session.query(Variable).filter_by(name='AI_MAX_TOKENS').first()
        if not ai_tokens:
            ai_tokens = Variable(
                name='AI_MAX_TOKENS',
                value=os.getenv('AI_MAX_TOKENS', '4096')
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


@pytest.fixture
def ai_interaction_tracker(request):
    """Track AI interactions for debugging and analysis.

    This fixture records all AI requests and responses during a test.
    If the test fails, the interactions are saved to a JSON file for debugging.
    """
    interactions = []

    def record(request_payload, response_data, status_code):
        """Record an AI interaction."""
        interactions.append({
            'request': request_payload,
            'response': response_data,
            'status': status_code,
            'timestamp': datetime.utcnow().isoformat()
        })

    yield record

    # Save interactions if test failed
    if request.node.rep_call.failed:
        test_name = request.node.name
        output_dir = 'test-results/ai-interactions'
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, f'{test_name}.json')
        with open(output_file, 'w') as f:
            json.dump({
                'test': test_name,
                'failed': True,
                'interactions': interactions
            }, f, indent=2)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for interaction tracker."""
    outcome = yield
    rep = outcome.get_result()

    # Store result in the item for access by fixtures
    setattr(item, f"rep_{rep.when}", rep)
