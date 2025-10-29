import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Response

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from app import app
from server_execution import try_server_execution


class TestServerIdentityIndependence(unittest.TestCase):
    """Ensure server execution responses do not depend on user identity."""

    def _invoke_for_user(self, user_id: str) -> Response:
        with app.test_request_context('/shared-server'):
            stub_server = SimpleNamespace(enabled=True)
            with patch(
                'server_execution.get_server_by_name',
                return_value=stub_server,
            ) as mock_get_server, patch(
                'server_execution.execute_server_code',
                side_effect=lambda *_, **__: Response('OK', mimetype='text/plain'),
            ):
                with patch('server_execution.current_user', new=SimpleNamespace(id=user_id)):
                    response = try_server_execution('/shared-server')
                mock_get_server.assert_called_with(user_id, 'shared-server')
                assert response is not None
                return response

    def test_try_server_execution_returns_same_response_for_any_user(self):
        default_response = self._invoke_for_user('default-user')
        alternate_response = self._invoke_for_user('alternate-user')

        self.assertEqual(default_response.status_code, alternate_response.status_code)
        self.assertEqual(default_response.get_data(), alternate_response.get_data())


if __name__ == '__main__':
    unittest.main()
