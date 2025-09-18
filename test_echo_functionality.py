import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

from app import app, db
from models import Server, User
from routes.core import not_found_error, get_existing_routes
from server_execution import try_server_execution, execute_server_code, is_potential_server_path


class TestEchoFunctionality(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user
        self.test_user = User(
            id='test_user_123',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_paid=True,
            current_terms_accepted=True
        )
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_echo_server_missing_from_database(self):
        """Test that no 'echo' server exists in the database"""
        echo_servers = Server.query.filter_by(name='echo').all()
        self.assertEqual(len(echo_servers), 0, "Expected no 'echo' servers in database")
    
    def test_is_potential_server_path_for_echo(self):
        """Test that /echo is identified as a potential server path"""
        existing_routes = get_existing_routes()
        result = is_potential_server_path('/echo', existing_routes)
        self.assertTrue(result, "/echo should be identified as a potential server path")
    
    def test_try_server_execution_without_authentication(self):
        """Test that server execution fails without authentication"""
        with app.test_request_context('/echo'):
            # Mock current_user as not authenticated
            with patch('server_execution.current_user') as mock_user:
                mock_user.is_authenticated = False
                result = try_server_execution('/echo')
                self.assertIsNone(result, "Should return None when user is not authenticated")
    
    def test_try_server_execution_with_authentication_but_no_server(self):
        """Test that server execution fails when authenticated but no echo server exists"""
        with app.test_request_context('/echo'):
            # Mock current_user as authenticated
            with patch('server_execution.current_user') as mock_user:
                mock_user.is_authenticated = True
                mock_user.id = self.test_user.id
                
                result = try_server_execution('/echo')
                self.assertIsNone(result, "Should return None when no echo server exists for user")
    
    def test_echo_server_creation_and_execution(self):
        """Test that echo server works when properly created"""
        # Create an echo server for the test user
        echo_server = Server(
            name='echo',
            definition='return {"output": "Hello, World!", "content_type": "text/html"}',
            user_id=self.test_user.id
        )
        db.session.add(echo_server)
        db.session.commit()
        
        with app.test_request_context('/echo'):
            # Mock current_user as authenticated
            with patch('server_execution.current_user') as mock_user:
                mock_user.is_authenticated = True
                mock_user.id = self.test_user.id

                # Mock the text function runner
                with patch('server_execution.run_text_function') as mock_runner:
                    mock_runner.return_value = {
                        'output': 'Hello, World!',
                        'content_type': 'text/html'
                    }
                    
                    result = try_server_execution('/echo')
                    self.assertIsNotNone(result, "Should return a result when echo server exists")
    
    def test_not_found_error_flow_for_echo(self):
        """Test the complete 404 error handler flow for /echo"""
        with app.test_request_context('/echo'):
            # Mock current_user as authenticated
            with patch('server_execution.current_user') as mock_user:
                mock_user.is_authenticated = True
                mock_user.id = self.test_user.id
                
                # Create a mock 404 error
                mock_error = MagicMock()
                
                # Call the not_found_error handler
                result = not_found_error(mock_error)
                
                # Should return a 404 response since no echo server exists
                self.assertEqual(result[1], 404, "Should return 404 status when no echo server exists")
    
    def test_echo_redirect_url_format(self):
        """Test that echo server generates correct CID redirect URL"""
        # Create an echo server
        echo_server = Server(
            name='echo',
            definition='return {"output": "<h1>Hello, World!</h1>", "content_type": "text/html"}',
            user_id=self.test_user.id
        )
        db.session.add(echo_server)
        db.session.commit()
        
        with app.test_request_context('/echo'):
            with patch('server_execution.current_user') as mock_user:
                mock_user.is_authenticated = True
                mock_user.id = self.test_user.id
                
                # Mock the text function runner
                with patch('server_execution.run_text_function') as mock_runner:
                    mock_runner.return_value = {
                        'output': '<h1>Hello, World!</h1>',
                        'content_type': 'text/html'
                    }
                    
                    result = execute_server_code(echo_server, 'echo')
                    
                    # Should be a redirect response
                    self.assertEqual(result.status_code, 302, "Should return redirect response")
                    
                    # Check that it redirects to a CID URL with .html extension
                    location = result.headers.get('Location')
                    self.assertIsNotNone(location, "Should have a Location header")
                    self.assertTrue(location.startswith('/bafybei'), "Should redirect to CID URL starting with /bafybei")
                    self.assertTrue(location.endswith('.html'), "Should redirect to .html URL for text/html content")


if __name__ == '__main__':
    unittest.main()
