"""Diagnostic test for OpenRouter API connectivity.

This test verifies that the OpenRouter API is accessible and working
before running the full AI evaluation suite. It provides detailed
diagnostic information on any failures.
"""

import os
import json

import pytest
import requests


def test_openrouter_api_connectivity(requires_openrouter_api_key):
    """Test basic OpenRouter API connectivity with detailed diagnostics.

    This test makes a minimal API call to verify:
    1. API key is valid
    2. Network connection works
    3. API response format is correct
    4. Basic model execution works

    Runs before other tests to fail fast if API is unavailable.
    """
    api_key = os.getenv('OPENROUTER_API_KEY')

    # Diagnostic: API key format
    print(f"\n{'='*70}")
    print("OpenRouter API Connectivity Diagnostics")
    print(f"{'='*70}")
    print(f"API Key present: {bool(api_key)}")
    if api_key:
        print(f"API Key format: {api_key[:15]}...{api_key[-4:]}")
        print(f"API Key length: {len(api_key)}")

    assert api_key, "OPENROUTER_API_KEY environment variable not set"

    # Test endpoint
    url = "https://openrouter.ai/api/v1/chat/completions"
    print(f"\nEndpoint: {url}")

    # Minimal test payload
    model = os.getenv('AI_MODEL', 'anthropic/claude-sonnet-4-20250514')
    print(f"Model: {model}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://viewer.app",
        "X-Title": "Viewer AI Eval Diagnostic Test",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a diagnostic test. Respond with exactly: OK"
            },
            {
                "role": "user",
                "content": "Test"
            }
        ],
        "max_tokens": 10,
        "temperature": 0.0
    }

    print(f"\nRequest payload:")
    print(json.dumps(payload, indent=2))

    # Make request with detailed error handling
    try:
        print(f"\nMaking request to OpenRouter...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"Response status: {response.status_code}")
        print(f"Response headers:")
        for key, value in response.headers.items():
            if key.lower() not in ['authorization', 'cookie', 'set-cookie']:
                print(f"  {key}: {value}")

        # Check status code
        if response.status_code != 200:
            print(f"\n{'='*70}")
            print("ERROR: Non-200 status code")
            print(f"{'='*70}")
            print(f"Status: {response.status_code}")
            print(f"\nResponse body:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))

                # Provide specific error guidance
                if response.status_code == 401:
                    print("\n❌ AUTHENTICATION FAILED")
                    print("   Check that OPENROUTER_API_KEY is valid")
                    print("   Get a key at: https://openrouter.ai/keys")
                elif response.status_code == 400:
                    print("\n❌ BAD REQUEST")
                    print("   The request format may be invalid")
                    if 'error' in error_data:
                        print(f"   Error: {error_data['error']}")
                elif response.status_code == 429:
                    print("\n❌ RATE LIMIT EXCEEDED")
                    print("   Wait a moment and try again")
                elif response.status_code == 402:
                    print("\n❌ INSUFFICIENT CREDITS")
                    print("   Add credits at: https://openrouter.ai/credits")

            except Exception as e:
                print(f"(Could not parse response as JSON: {e})")
                print(response.text[:500])

            pytest.fail(f"OpenRouter API returned status {response.status_code}")

        # Parse response
        print(f"\nResponse body:")
        data = response.json()
        print(json.dumps(data, indent=2))

        # Verify response structure
        assert 'choices' in data, "Response missing 'choices' field"
        assert len(data['choices']) > 0, "Response has no choices"
        assert 'message' in data['choices'][0], "Choice missing 'message' field"
        assert 'content' in data['choices'][0]['message'], "Message missing 'content' field"

        content = data['choices'][0]['message']['content']
        print(f"\nAI Response content: '{content}'")

        # Success
        print(f"\n{'='*70}")
        print("✓ OpenRouter API connectivity test PASSED")
        print(f"{'='*70}")
        print(f"✓ Authentication successful")
        print(f"✓ Model {model} accessible")
        print(f"✓ API responding correctly")
        print(f"{'='*70}\n")

    except requests.exceptions.Timeout:
        print(f"\n{'='*70}")
        print("ERROR: Request timed out")
        print(f"{'='*70}")
        pytest.fail("OpenRouter API request timed out after 30s")

    except requests.exceptions.ConnectionError as e:
        print(f"\n{'='*70}")
        print("ERROR: Connection failed")
        print(f"{'='*70}")
        print(f"Details: {e}")
        pytest.fail("Could not connect to OpenRouter API - check network connection")

    except Exception as e:
        print(f"\n{'='*70}")
        print("ERROR: Unexpected error")
        print(f"{'='*70}")
        print(f"Type: {type(e).__name__}")
        print(f"Details: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Unexpected error during OpenRouter API test: {e}")


def test_ai_assist_server_exists(memory_client):
    """Test that ai_assist server is properly configured.

    This diagnostic test verifies the server setup before making API calls.
    """
    print(f"\n{'='*70}")
    print("AI Assist Server Configuration Diagnostics")
    print(f"{'='*70}")

    from models import Server, Secret, Variable
    from database import db

    with memory_client.application.app_context():
        # Check server exists
        ai_server = db.session.query(Server).filter_by(name='ai_assist').first()
        print(f"ai_assist server exists: {ai_server is not None}")

        if ai_server:
            print(f"ai_assist enabled: {ai_server.enabled}")
            print(f"Definition length: {len(ai_server.definition)} characters")

        # Check secret exists
        secret = db.session.query(Secret).filter_by(name='OPENROUTER_API_KEY').first()
        print(f"OPENROUTER_API_KEY secret exists: {secret is not None}")

        # Check variables
        ai_model = db.session.query(Variable).filter_by(name='AI_MODEL').first()
        print(f"AI_MODEL variable: {ai_model.definition if ai_model else 'NOT SET'}")

        ai_temp = db.session.query(Variable).filter_by(name='AI_TEMPERATURE').first()
        print(f"AI_TEMPERATURE variable: {ai_temp.definition if ai_temp else 'NOT SET'}")

        ai_tokens = db.session.query(Variable).filter_by(name='AI_MAX_TOKENS').first()
        print(f"AI_MAX_TOKENS variable: {ai_tokens.definition if ai_tokens else 'NOT SET'}")

        print(f"{'='*70}\n")

        assert ai_server is not None, "ai_assist server not found in database"
        assert ai_server.enabled, "ai_assist server is disabled"
        assert secret is not None, "OPENROUTER_API_KEY secret not found"


def test_ai_assist_minimal_request(memory_client, requires_openrouter_api_key):
    """Test minimal AI assist request with detailed diagnostics.

    This makes the simplest possible request to the ai_assist server
    to verify the full pipeline works.
    """
    print(f"\n{'='*70}")
    print("AI Assist Server Request Diagnostics")
    print(f"{'='*70}")

    payload = {
        'request_text': 'Say "test successful"',
        'original_text': '',
        'target_label': 'diagnostic test',
        'context_data': {},
        'form_summary': {}
    }

    print(f"Request payload:")
    print(json.dumps(payload, indent=2))

    print(f"\nMaking POST request to /ai...")
    response = memory_client.post('/ai', json=payload, follow_redirects=True)

    print(f"Response status: {response.status_code}")
    print(f"Response content type: {response.content_type}")

    if response.status_code != 200:
        print(f"\n{'='*70}")
        print("ERROR: Non-200 status from /ai endpoint")
        print(f"{'='*70}")
        print(f"Response body:")
        print(response.get_data(as_text=True))
        pytest.fail(f"Expected status 200, got {response.status_code}")

    data = response.get_json()
    print(f"\nResponse JSON:")
    print(json.dumps(data, indent=2))

    # Check for errors in response
    if 'error' in data:
        print(f"\n{'='*70}")
        print("ERROR: AI response contains error field")
        print(f"{'='*70}")
        print(f"Error: {data['error']}")
        print(f"Message: {data.get('message', 'N/A')}")
        pytest.fail(f"AI request failed: {data.get('message', data['error'])}")

    assert 'updated_text' in data, "Response missing 'updated_text' field"

    updated_text = data['updated_text']
    print(f"\nUpdated text: '{updated_text}'")

    assert len(updated_text) > 0, "AI returned empty response"

    print(f"\n{'='*70}")
    print("✓ AI Assist server request test PASSED")
    print(f"{'='*70}\n")
