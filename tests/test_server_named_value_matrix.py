"""Unit tests for server named value matrix helper."""
from __future__ import annotations

import unittest

from app import app
from models import Server
from routes.servers import _build_named_value_matrix


class TestServerNamedValueMatrix(unittest.TestCase):
    """Verify status calculations for named value grid."""

    def setUp(self) -> None:
        self.app = app
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        self.app_context.pop()

    def test_cookie_overrides_variable_and_secret_entries(self):
        """Cookies should mark lower-priority sources as overridden."""

        server = Server(
            name='svc',
            definition=(
                "def main(city, API_KEY):\n"
                "    return {'output': city}\n"
            ),
        )

        with self.app.test_request_context('/servers/svc', headers={'Cookie': 'city=cookie-city'}):
            matrix = _build_named_value_matrix(
                server,
                available_variables={'city'},
                available_secrets={'API_KEY'},
            )

        rows = {row['name']: row for row in matrix['rows']}
        self.assertEqual(rows['city']['sources']['cookies']['status'], 'defined')
        self.assertEqual(rows['city']['sources']['variables']['status'], 'overridden')
        self.assertEqual(rows['city']['sources']['secrets']['status'], 'none')
        self.assertEqual(rows['API_KEY']['sources']['secrets']['status'], 'defined')

    def test_missing_sources_are_marked_none(self):
        """Absent sources should be surfaced even when no data exists."""

        server = Server(
            name='empty',
            definition=(
                "def main(user, TOKEN):\n"
                "    return user\n"
            ),
        )

        with self.app.test_request_context('/servers/empty'):
            matrix = _build_named_value_matrix(
                server,
                available_variables=set(),
                available_secrets=set(),
                available_cookies=set(),
            )

        rows = {row['name']: row for row in matrix['rows']}
        self.assertEqual(rows['user']['sources']['variables']['status'], 'none')
        self.assertEqual(rows['user']['sources']['secrets']['status'], 'none')
        self.assertEqual(rows['TOKEN']['sources']['secrets']['status'], 'none')


if __name__ == '__main__':
    unittest.main()
