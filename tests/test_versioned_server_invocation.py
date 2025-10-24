#!/usr/bin/env python3
"""
Tests for versioned server invocation via /{server_name}/{partial_CID}.

Covers:
- Path detection by is_potential_versioned_server_path()
- try_server_execution_with_partial() behavior for 0/1/many matches
- Server existence guards
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

from server_execution import (  # noqa: E402
    is_potential_versioned_server_path,
    try_server_execution_with_partial,
)


class TestVersionedServerInvocation(unittest.TestCase):
    def setUp(self):
        self.user_id = 'user_1'
        self.server_name = 'my_server'

    def test_is_potential_versioned_server_path(self):
        existing = {'/servers', '/uploads', '/server_events'}
        self.assertTrue(is_potential_versioned_server_path('/foo/abc', existing))
        self.assertFalse(is_potential_versioned_server_path('/', existing))
        self.assertFalse(is_potential_versioned_server_path('/foo', existing))  # only one segment
        self.assertFalse(is_potential_versioned_server_path('/servers/abc', existing))  # collides with existing route root
        self.assertTrue(is_potential_versioned_server_path('/foo/abc/helper', existing))
        self.assertFalse(is_potential_versioned_server_path('/a/b/c/d', existing))  # too many segments

    @patch('server_execution.get_server_by_name')
    @patch('server_execution.current_user')
    def test_try_partial_server_missing(self, mock_current_user, mock_get_server_by_name):
        mock_current_user.id = self.user_id
        mock_get_server_by_name.return_value = None
        result = try_server_execution_with_partial(f'/{self.server_name}/abc', Mock())
        self.assertIsNone(result)

    @patch('server_execution.render_template')
    @patch('server_execution.get_server_by_name')
    @patch('server_execution.current_user')
    def test_try_partial_no_matches_returns_404(self, mock_current_user, mock_get_server_by_name, mock_render):
        mock_current_user.id = self.user_id
        mock_get_server_by_name.return_value = object()
        mock_render.return_value = ('not found', 404)
        history_fetcher = Mock(return_value=[])
        _, status = try_server_execution_with_partial(f'/{self.server_name}/abc', history_fetcher)
        self.assertEqual(status, 404)
        mock_render.assert_called()

    @patch('server_execution.jsonify')
    @patch('server_execution.get_server_by_name')
    @patch('server_execution.current_user')
    def test_try_partial_multiple_matches_returns_400_with_list(self, mock_current_user, mock_get_server_by_name, mock_jsonify):
        mock_current_user.id = self.user_id
        mock_get_server_by_name.return_value = object()
        # Two matches with same prefix
        history_fetcher = Mock(return_value=[
            {'definition_cid': 'abcd1234', 'snapshot_cid': 'snap1', 'created_at': None},
            {'definition_cid': 'abcd5678', 'snapshot_cid': 'snap2', 'created_at': None},
        ])
        mock_jsonify.side_effect = lambda payload: payload  # return payload directly for inspection
        payload, status = try_server_execution_with_partial(f'/{self.server_name}/abcd', history_fetcher)
        self.assertEqual(status, 400)
        self.assertIn('matches', payload)
        self.assertEqual(len(payload['matches']), 2)

    @patch('server_execution.execute_server_code_from_definition')
    @patch('server_execution.get_server_by_name')
    @patch('server_execution.current_user')
    def test_try_partial_single_match_executes(self, mock_current_user, mock_get_server_by_name, mock_execute):
        mock_current_user.id = self.user_id
        mock_get_server_by_name.return_value = object()
        history_fetcher = Mock(return_value=[
            {
                'definition_cid': 'abc123',
                'snapshot_cid': 'snapcid',
                'definition': "print('v1')",
                'created_at': None,
            }
        ])
        mock_execute.return_value = 'EXECUTED'
        result = try_server_execution_with_partial(f'/{self.server_name}/abc', history_fetcher)
        self.assertEqual(result, 'EXECUTED')
        mock_execute.assert_called_once()

    @patch('server_execution.execute_server_function_from_definition')
    @patch('server_execution.get_server_by_name')
    @patch('server_execution.current_user')
    def test_try_partial_helper_executes(self, mock_current_user, mock_get_server_by_name, mock_execute_helper):
        mock_current_user.id = self.user_id
        mock_get_server_by_name.return_value = object()
        history_entry = {
            'definition_cid': 'abc123',
            'snapshot_cid': 'snapcid',
            'definition': "def helper(label):\n    return {'output': label, 'content_type': 'text/plain'}\n",
            'created_at': None,
        }
        history_fetcher = Mock(return_value=[history_entry])
        mock_execute_helper.return_value = 'HELPER'

        result = try_server_execution_with_partial(
            f'/{self.server_name}/abc/helper', history_fetcher
        )

        self.assertEqual(result, 'HELPER')
        mock_execute_helper.assert_called_once_with(
            history_entry['definition'], self.server_name, 'helper'
        )


if __name__ == '__main__':
    unittest.main()
