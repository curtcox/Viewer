"""Integration tests for authorization with Flask app."""

import json
import pytest
from unittest.mock import patch

from authorization import AuthorizationResult


class TestAuthorizationIntegration:
    """Integration tests for authorization with actual HTTP requests."""
    
    def test_successful_request_returns_200(self, memory_client):
        """Test that authorized requests return successfully."""
        response = memory_client.get('/')
        assert response.status_code == 200
    
    def test_successful_api_request(self, memory_client):
        """Test that authorized API requests succeed."""
        response = memory_client.get('/routes')
        assert response.status_code == 200
    
    @patch('app.authorize_request')
    def test_rejected_request_returns_401_html(self, mock_authorize, memory_client):
        """Test that rejected requests return 401 with HTML."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=401,
            message="Authentication required"
        )
        
        response = memory_client.get('/', headers={'Accept': 'text/html'})
        assert response.status_code == 401
        assert b'401' in response.data
        assert b'Authentication' in response.data
    
    @patch('app.authorize_request')
    def test_rejected_request_returns_403_html(self, mock_authorize, memory_client):
        """Test that rejected requests return 403 with HTML."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=403,
            message="Access denied"
        )
        
        response = memory_client.get('/', headers={'Accept': 'text/html'})
        assert response.status_code == 403
        assert b'403' in response.data
        assert b'Forbidden' in response.data
    
    @patch('app.authorize_request')
    def test_rejected_api_request_returns_json_401(self, mock_authorize, memory_client):
        """Test that rejected API requests return JSON with 401."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=401,
            message="API authentication required"
        )
        
        response = memory_client.get('/api/routes', headers={'Accept': 'application/json'})
        assert response.status_code == 401
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert data['error'] == 'Authorization failed'
        assert data['status'] == 401
        assert data['message'] == 'API authentication required'
    
    @patch('app.authorize_request')
    def test_rejected_api_request_returns_json_403(self, mock_authorize, memory_client):
        """Test that rejected API requests return JSON with 403."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=403,
            message="API access denied"
        )
        
        response = memory_client.get('/api/routes', headers={'Accept': 'application/json'})
        assert response.status_code == 403
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert data['error'] == 'Authorization failed'
        assert data['status'] == 403
        assert data['message'] == 'API access denied'
    
    @patch('app.authorize_request')
    def test_rejected_text_request_returns_plain_text(self, mock_authorize, memory_client):
        """Test that rejected text requests return plain text."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=401,
            message="Text authentication required"
        )
        
        response = memory_client.get('/test', headers={'Accept': 'text/plain'})
        assert response.status_code == 401
        assert 'text/plain' in response.content_type
        assert b'Error 401' in response.data
        assert b'Text authentication required' in response.data
    
    @patch('app.authorize_request')
    def test_post_request_authorization(self, mock_authorize, memory_client):
        """Test that POST requests are also authorized."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=403,
            message="POST not allowed"
        )
        
        response = memory_client.post('/aliases/new', headers={'Accept': 'application/json'})
        assert response.status_code == 403
    
    @patch('app.authorize_request')
    def test_put_request_authorization(self, mock_authorize, memory_client):
        """Test that PUT requests are also authorized."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=403,
            message="PUT not allowed"
        )
        
        response = memory_client.put('/api/test', headers={'Accept': 'application/json'})
        assert response.status_code == 403
    
    @patch('app.authorize_request')
    def test_delete_request_authorization(self, mock_authorize, memory_client):
        """Test that DELETE requests are also authorized."""
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=403,
            message="DELETE not allowed"
        )
        
        response = memory_client.delete('/api/test', headers={'Accept': 'application/json'})
        assert response.status_code == 403
    
    def test_multiple_successful_requests(self, memory_client):
        """Test that multiple successful requests work."""
        for _ in range(5):
            response = memory_client.get('/')
            assert response.status_code == 200
    
    @patch('app.authorize_request')
    def test_mixed_authorized_and_rejected_requests(self, mock_authorize, memory_client):
        """Test mixing authorized and rejected requests."""
        # First request allowed
        mock_authorize.return_value = AuthorizationResult(allowed=True)
        response = memory_client.get('/')
        assert response.status_code == 200
        
        # Second request rejected
        mock_authorize.return_value = AuthorizationResult(
            allowed=False,
            status_code=401,
            message="Now authentication required"
        )
        response = memory_client.get('/')
        assert response.status_code == 401
        
        # Third request allowed again
        mock_authorize.return_value = AuthorizationResult(allowed=True)
        response = memory_client.get('/')
        assert response.status_code == 200
