"""Integration tests for authorization handler."""

import json
import pytest

from authorization import AuthorizationResult
from authorization_handler import create_authorization_error_response


class TestCreateAuthorizationErrorResponse:
    """Tests for create_authorization_error_response function."""
    
    def test_json_error_response_401(self, memory_db_app):
        """Test JSON error response for 401."""
        with memory_db_app.test_request_context(
            '/api/test',
            headers={'Accept': 'application/json'}
        ):
            result = AuthorizationResult(
                allowed=False,
                status_code=401,
                message="Authentication required"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 401
            assert response.content_type == 'application/json'
            
            data = json.loads(response.get_data(as_text=True))
            assert data['error'] == 'Authorization failed'
            assert data['status'] == 401
            assert data['message'] == 'Authentication required'
    
    def test_json_error_response_403(self, memory_db_app):
        """Test JSON error response for 403."""
        with memory_db_app.test_request_context(
            '/api/test',
            headers={'Accept': 'application/json'}
        ):
            result = AuthorizationResult(
                allowed=False,
                status_code=403,
                message="Access denied"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 403
            assert response.content_type == 'application/json'
            
            data = json.loads(response.get_data(as_text=True))
            assert data['error'] == 'Authorization failed'
            assert data['status'] == 403
            assert data['message'] == 'Access denied'
    
    def test_text_error_response_401(self, memory_db_app):
        """Test plain text error response for 401."""
        with memory_db_app.test_request_context(
            '/test',
            headers={'Accept': 'text/plain'}
        ):
            result = AuthorizationResult(
                allowed=False,
                status_code=401,
                message="Authentication required"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 401
            assert response.content_type == 'text/plain; charset=utf-8'
            assert 'Error 401' in response.get_data(as_text=True)
            assert 'Authentication required' in response.get_data(as_text=True)
    
    def test_text_error_response_403(self, memory_db_app):
        """Test plain text error response for 403."""
        with memory_db_app.test_request_context(
            '/test',
            headers={'Accept': 'text/plain'}
        ):
            result = AuthorizationResult(
                allowed=False,
                status_code=403,
                message="Access denied"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 403
            assert response.content_type == 'text/plain; charset=utf-8'
            assert 'Error 403' in response.get_data(as_text=True)
            assert 'Access denied' in response.get_data(as_text=True)
    
    def test_html_error_response_401(self, memory_db_app):
        """Test HTML error response for 401."""
        with memory_db_app.test_request_context(
            '/test',
            headers={'Accept': 'text/html'}
        ):
            result = AuthorizationResult(
                allowed=False,
                status_code=401,
                message="Authentication required"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 401
            assert 'text/html' in response.content_type
            html = response.get_data(as_text=True)
            assert '401' in html
            assert 'Authentication' in html
    
    def test_html_error_response_403(self, memory_db_app):
        """Test HTML error response for 403."""
        with memory_db_app.test_request_context(
            '/test',
            headers={'Accept': 'text/html'}
        ):
            result = AuthorizationResult(
                allowed=False,
                status_code=403,
                message="Access denied"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 403
            assert 'text/html' in response.content_type
            html = response.get_data(as_text=True)
            assert '403' in html
            assert 'Forbidden' in html
    
    def test_api_path_returns_json_without_accept_header(self, memory_db_app):
        """Test that /api/ paths return JSON even without Accept header."""
        with memory_db_app.test_request_context('/api/test'):
            result = AuthorizationResult(
                allowed=False,
                status_code=401,
                message="Authentication required"
            )
            response = create_authorization_error_response(result)
            
            assert response.status_code == 401
            assert response.content_type == 'application/json'
    
    def test_raises_error_for_allowed_result(self, memory_db_app):
        """Test that calling with allowed=True raises ValueError."""
        with memory_db_app.test_request_context('/test'):
            result = AuthorizationResult(allowed=True)
            with pytest.raises(ValueError, match="allowed=True"):
                create_authorization_error_response(result)
