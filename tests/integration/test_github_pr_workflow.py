"""Integration tests for GitHub PR import/export workflows."""
import json
import unittest
from unittest.mock import patch

try:
    import github  # noqa: F401
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("PyGithub dependency is not installed") from exc

from app import create_app, db
from models import Alias, Server, Variable


class TestGitHubPRIntegration(unittest.TestCase):
    """Integration tests for GitHub PR workflows."""

    def setUp(self):
        """Set up test app and database."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
            'DEBUG': False,
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up database."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def authenticate(self):
        """Mark the test client's session as authenticated."""
        with self.client.session_transaction() as session:
            session['_fresh'] = True

    @patch('routes.import_export.github_pr.create_export_pr')
    def test_export_to_github_pr_flow(self, mock_create_pr):
        """Test complete export to GitHub PR flow."""
        self.authenticate()

        # Create some test data
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='literal /test -> /prod')
            server = Server(name='test-server', definition='def main():\n    return "test"')
            variable = Variable(name='test-var', definition='test-value')
            db.session.add_all([alias, server, variable])
            db.session.commit()

        # Mock PR creation
        mock_create_pr.return_value = {
            'url': 'https://api.github.com/repos/owner/repo/pulls/1',
            'number': 1,
            'html_url': 'https://github.com/owner/repo/pull/1',
            'branch_name': 'viewer-export-test',
            'target_repo': 'owner/repo',
        }

        # Submit export form with GitHub PR details
        response = self.client.post('/export', data={
            'snapshot': 'y',
            'include_aliases': 'y',
            'include_servers': 'y',
            'include_variables': 'y',
            'include_cid_map': 'y',
            'github_target_repo': 'owner/repo',
            'github_token': 'test_token',
            'github_pr_title': 'Test PR',
            'github_pr_description': 'Test description',
            'submit_github_pr': 'Create Pull Request',
        }, follow_redirects=False)

        # Verify PR was created
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pull request created successfully', response.data)
        self.assertIn(b'https://github.com/owner/repo/pull/1', response.data)

        # Verify mock was called with correct parameters
        mock_create_pr.assert_called_once()
        call_args = mock_create_pr.call_args
        self.assertEqual(call_args.kwargs['target_repo'], 'owner/repo')
        self.assertEqual(call_args.kwargs['github_token'], 'test_token')
        self.assertEqual(call_args.kwargs['pr_title'], 'Test PR')
        self.assertEqual(call_args.kwargs['pr_description'], 'Test description')

        # Verify export JSON contains expected data
        export_json = call_args.kwargs['export_json']
        export_data = json.loads(export_json)
        self.assertEqual(export_data['version'], 6)
        self.assertIn('aliases', export_data)
        self.assertIn('servers', export_data)
        self.assertIn('variables', export_data)

    @patch('routes.import_export.github_pr.fetch_pr_export_data')
    def test_import_from_github_pr_flow(self, mock_fetch_pr):
        """Test complete import from GitHub PR flow."""
        self.authenticate()

        # Create simple export data to import
        export_data = {
            'version': 6,
            'runtime': 'test_cid_runtime',
            'project_files': 'test_cid_project',
            'cid_values': {
                'test_cid_runtime': '{"python": {"version": "3.12"}}',
                'test_cid_project': '{}',
            }
        }

        # Mock PR fetch to return export data
        mock_fetch_pr.return_value = (json.dumps(export_data), None)

        # Submit import form with GitHub PR URL
        response = self.client.post('/import', data={
            'import_source': 'github_pr',
            'github_pr_url': 'https://github.com/owner/repo/pull/123',
            'github_import_token': 'test_token',
            'include_aliases': 'y',
            'process_cid_map': 'y',
            'submit': 'Import Data',
        }, follow_redirects=True)

        # Verify import succeeded (should show import page with success)
        self.assertEqual(response.status_code, 200)

        # Verify mock was called with correct parameters
        mock_fetch_pr.assert_called_once_with(
            'https://github.com/owner/repo/pull/123',
            'test_token'
        )

    @patch('routes.import_export.github_pr.create_export_pr')
    def test_export_pr_error_handling(self, mock_create_pr):
        """Test error handling when PR creation fails."""
        self.authenticate()

        # Create test data
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='literal /test -> /prod')
            db.session.add(alias)
            db.session.commit()

        # Mock PR creation failure
        from routes.import_export.github_pr import GitHubPRError
        mock_create_pr.side_effect = GitHubPRError(
            'Failed to access repository',
            details={'status': 404, 'owner': 'owner', 'repo': 'repo'}
        )

        # Submit export form
        response = self.client.post('/export', data={
            'snapshot': 'y',
            'include_aliases': 'y',
            'github_target_repo': 'owner/repo',
            'github_token': 'test_token',
            'submit_github_pr': 'Create Pull Request',
        }, follow_redirects=False)

        # Verify error is displayed
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Failed to create pull request', response.data)
        self.assertIn(b'Failed to access repository', response.data)

    @patch('routes.import_export.github_pr.fetch_pr_export_data')
    def test_import_pr_error_handling(self, mock_fetch_pr):
        """Test error handling when PR fetch fails."""
        self.authenticate()

        # Mock PR fetch failure
        mock_fetch_pr.return_value = (None, 'Pull request does not modify the boot image file')

        # Submit import form
        response = self.client.post('/import', data={
            'import_source': 'github_pr',
            'github_pr_url': 'https://github.com/owner/repo/pull/456',
            'include_aliases': 'y',
            'submit': 'Import Data',
        }, follow_redirects=False)

        # Verify error is handled
        self.assertEqual(response.status_code, 200)
        # The error should be displayed in the form
        self.assertIn(b'does not modify the boot image file', response.data)

    def test_export_missing_github_fields(self):
        """Test validation when GitHub fields are missing."""
        self.authenticate()

        # Create test data
        with self.app.app_context():
            alias = Alias(name='test-alias', definition='literal /test -> /prod')
            db.session.add(alias)
            db.session.commit()

        # Submit without required fields
        response = self.client.post('/export', data={
            'snapshot': 'y',
            'include_aliases': 'y',
            'submit_github_pr': 'Create Pull Request',
        }, follow_redirects=False)

        # Verify validation error
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Target repository is required', response.data)

    def test_import_missing_github_pr_url(self):
        """Test validation when GitHub PR URL is missing."""
        self.authenticate()

        # Submit without PR URL
        response = self.client.post('/import', data={
            'import_source': 'github_pr',
            'include_aliases': 'y',
            'submit': 'Import Data',
        }, follow_redirects=False)

        # Verify validation error
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GitHub PR URL is required', response.data)


if __name__ == '__main__':
    unittest.main()
