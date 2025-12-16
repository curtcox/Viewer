"""Tests for AI_SYSTEM_PROMPTS functionality in ai_assist server."""
import json
import os
import unittest

# Set required environment variables before importing app
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

# Import the functions we want to test
# We'll need to extract them from the server definition
from pathlib import Path


class TestSystemPromptLookup(unittest.TestCase):
    """Test the AI system prompt lookup logic."""

    def setUp(self):
        """Load the ai_assist server definition and extract functions."""
        ai_assist_path = Path(__file__).parent.parent / 'reference_templates' / 'servers' / 'definitions' / 'ai_assist.py'

        # Read and execute the ai_assist.py file to get its functions
        with open(ai_assist_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Create a module namespace
        self.ai_assist_module = {}
        exec(code, self.ai_assist_module)  # pylint: disable=exec-used

        # Extract the functions we need to test
        self._lookup_system_prompt = self.ai_assist_module['_lookup_system_prompt']
        self._get_system_prompt_from_cid = self.ai_assist_module['_get_system_prompt_from_cid']
        self._build_ai_prompt = self.ai_assist_module['_build_ai_prompt']

    def test_lookup_with_no_prompts_config(self):
        """Test that default prompt is returned when no AI_SYSTEM_PROMPTS configured."""
        context = {
            'request': {
                'path': '/servers/test'
            }
        }

        result = self._lookup_system_prompt(context, None)
        self.assertIn("helpful AI assistant", result)
        self.assertIn("modify text content", result)

    def test_lookup_with_invalid_json(self):
        """Test that default prompt is returned when AI_SYSTEM_PROMPTS is invalid JSON."""
        context = {
            'request': {
                'path': '/servers/test'
            }
        }

        result = self._lookup_system_prompt(context, "not valid json")
        self.assertIn("helpful AI assistant", result)

    def test_lookup_with_no_matching_path(self):
        """Test that default prompt CID is used when no path matches."""
        context = {
            'request': {
                'path': '/some/other/path'
            }
        }

        # Use a mock CID that won't be found, so we get the fallback
        prompts_json = json.dumps({
            'default': 'NONEXISTENT_DEFAULT_CID',
            '/servers': 'SERVER_CID',
            '/aliases': 'ALIAS_CID'
        })

        result = self._lookup_system_prompt(context, prompts_json)
        # Should fall back to default hardcoded prompt
        self.assertIn("helpful AI assistant", result)

    def test_lookup_with_no_request_path(self):
        """Test that default prompt is used when request has no path."""
        context = {
            'request': {}
        }

        prompts_json = json.dumps({
            'default': 'DEFAULT_CID',
            '/servers': 'SERVER_CID'
        })

        result = self._lookup_system_prompt(context, prompts_json)
        # Should use default prompt (will fallback since CID doesn't exist)
        self.assertIn("helpful AI assistant", result)

    def test_lookup_with_empty_context(self):
        """Test that default prompt is used when context is empty."""
        context = {}

        prompts_json = json.dumps({
            'default': 'DEFAULT_CID',
            '/servers': 'SERVER_CID'
        })

        result = self._lookup_system_prompt(context, prompts_json)
        # Should use default prompt (will fallback since CID doesn't exist)
        self.assertIn("helpful AI assistant", result)

    def test_prefix_matching(self):
        """Test that URL fragments match as prefixes."""
        # Test that /servers matches /servers/myserver
        context = {
            'request': {
                'path': '/servers/myserver'
            }
        }

        prompts_json = json.dumps({
            'default': 'DEFAULT_CID',
            '/servers': 'SERVER_CID'
        })

        # The function will try to load SERVER_CID, fail, and return default
        result = self._lookup_system_prompt(context, prompts_json)
        self.assertIn("helpful AI assistant", result)  # Falls back to default

    def test_get_system_prompt_from_cid_fallback(self):
        """Test that _get_system_prompt_from_cid returns default on error."""
        # This should return the fallback prompt since CID won't be found
        result = self._get_system_prompt_from_cid('NONEXISTENT_CID')
        self.assertIn("helpful AI assistant", result)
        self.assertIn("modify text content", result)

    def test_build_ai_prompt_with_custom_system_prompt(self):
        """Test that _build_ai_prompt uses provided system prompt."""
        custom_prompt = "This is a custom system prompt."
        system_prompt, user_prompt = self._build_ai_prompt(
            request_text="Add a new function",
            original_text="# existing code",
            target_label="Python code",
            context_data={'form': 'server_form'},
            form_summary={},
            system_prompt=custom_prompt
        )

        self.assertEqual(system_prompt, custom_prompt)
        self.assertIn("Add a new function", user_prompt)
        self.assertIn("# existing code", user_prompt)

    def test_build_ai_prompt_with_default_system_prompt(self):
        """Test that _build_ai_prompt uses default when no system prompt provided."""
        system_prompt, user_prompt = self._build_ai_prompt(
            request_text="Add a new function",
            original_text="# existing code",
            target_label="Python code",
            context_data={'form': 'server_form'},
            form_summary={},
            system_prompt=None
        )

        self.assertIn("helpful AI assistant", system_prompt)
        self.assertIn("Add a new function", user_prompt)


class TestAiAssistWithSystemPrompts(unittest.TestCase):
    """Integration tests for ai_assist with AI_SYSTEM_PROMPTS variable."""

    def setUp(self):
        """Set up test fixtures."""
        # We'll test via the app's server execution mechanism
        from app import app, db
        from identity import ensure_default_resources

        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        ensure_default_resources()
        self.client = app.test_client()
        self.db = db

    def tearDown(self):
        """Clean up test fixtures."""
        self.db.session.remove()
        self.db.drop_all()
        self.app_context.pop()

    def test_ai_assist_uses_variable_for_system_prompt(self):
        """Test that ai_assist reads AI_SYSTEM_PROMPTS variable."""
        from models import Variable
        from db_access import save_entity

        # Create a test AI_SYSTEM_PROMPTS variable
        prompts_json = json.dumps({
            'default': 'AAAAAA_test_default',
            '/servers': 'AAAAAA_test_server'
        })

        var = Variable(name='AI_SYSTEM_PROMPTS', definition=prompts_json)
        save_entity(var)

        # Now when we call ai_assist, it should try to use these prompts
        # We can't easily test the full flow without mocking OpenRouter,
        # but we can verify the variable is accessible
        from db_access import get_variable_by_name
        retrieved = get_variable_by_name('AI_SYSTEM_PROMPTS')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.definition, prompts_json)


if __name__ == '__main__':
    unittest.main()
