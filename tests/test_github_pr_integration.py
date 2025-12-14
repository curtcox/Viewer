"""Unit tests for GitHub PR integration."""
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from github import GithubException
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("PyGithub dependency is not installed") from exc

from routes.import_export.github_pr import (
    GitHubPRError,
    create_export_pr,
    fetch_pr_export_data,
    parse_github_pr_url,
    prepare_boot_image_update,
)

from cid_core import generate_cid
from generate_boot_image import BootImageGenerator


class TestParseGitHubPRURL(unittest.TestCase):
    """Test GitHub PR URL parsing."""

    def test_parse_valid_pr_url(self):
        """Test parsing a valid GitHub PR URL."""
        owner, repo, pr_number = parse_github_pr_url('https://github.com/owner/repo/pull/123')
        self.assertEqual(owner, 'owner')
        self.assertEqual(repo, 'repo')
        self.assertEqual(pr_number, 123)

    def test_parse_valid_pr_url_with_www(self):
        """Test parsing a valid GitHub PR URL with www."""
        owner, repo, pr_number = parse_github_pr_url('https://www.github.com/owner/repo/pull/456')
        self.assertEqual(owner, 'owner')
        self.assertEqual(repo, 'repo')
        self.assertEqual(pr_number, 456)

    def test_parse_invalid_hostname(self):
        """Test parsing URL with invalid hostname."""
        owner, repo, pr_number = parse_github_pr_url('https://gitlab.com/owner/repo/pull/123')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        self.assertIsNone(pr_number)

    def test_parse_invalid_path(self):
        """Test parsing URL with invalid path."""
        owner, repo, pr_number = parse_github_pr_url('https://github.com/owner/repo/issues/123')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        self.assertIsNone(pr_number)

    def test_parse_missing_pr_number(self):
        """Test parsing URL missing PR number."""
        owner, repo, pr_number = parse_github_pr_url('https://github.com/owner/repo/pull/')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        self.assertIsNone(pr_number)

    def test_parse_invalid_pr_number(self):
        """Test parsing URL with non-numeric PR number."""
        owner, repo, pr_number = parse_github_pr_url('https://github.com/owner/repo/pull/abc')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        self.assertIsNone(pr_number)

    def test_parse_malformed_url(self):
        """Test parsing malformed URL."""
        owner, repo, pr_number = parse_github_pr_url('not-a-url')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
        self.assertIsNone(pr_number)


class TestCreateExportPR(unittest.TestCase):
    """Test creating GitHub pull requests with export data."""

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    @patch('routes.import_export.github_pr.prepare_boot_image_update')
    def test_create_pr_success(self, mock_prepare, mock_get_repo, mock_get_client):
        """Test successfully creating a PR."""
        mock_prepare.return_value = {
            'mode': 'prepared',
            'changed_paths': ['reference_templates/default.boot.json'],
        }

        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.default_branch = 'main'
        mock_get_repo.return_value = mock_repo

        # Mock ref and commit
        mock_ref = MagicMock()
        mock_ref.object.sha = 'abc123'
        mock_repo.get_git_ref.return_value = mock_ref

        # Mock file content (doesn't exist)
        mock_repo.get_contents.side_effect = GithubException(404, {'message': 'Not Found'}, None)

        # Mock PR creation
        mock_pr = MagicMock()
        mock_pr.url = 'https://api.github.com/repos/owner/repo/pulls/1'
        mock_pr.number = 1
        mock_pr.html_url = 'https://github.com/owner/repo/pull/1'
        mock_repo.create_pull.return_value = mock_pr

        # Test
        export_json = '{"test": "data"}'
        result = create_export_pr(
            export_json=export_json,
            target_repo='owner/repo',
            github_token='test_token',
        )

        # Assertions
        self.assertEqual(result['number'], 1)
        self.assertEqual(result['html_url'], 'https://github.com/owner/repo/pull/1')
        self.assertEqual(result['target_repo'], 'owner/repo')
        self.assertIn('branch_name', result)
        self.assertEqual(result.get('mode'), 'github')

        # Verify repository interactions
        mock_repo.create_git_ref.assert_called_once()
        mock_repo.create_file.assert_called_once()
        mock_repo.create_pull.assert_called_once()

    @patch('routes.import_export.github_pr.prepare_boot_image_update')
    def test_create_pr_missing_token_returns_manual_mode(self, mock_prepare):
        """Test creating PR without token returns manual preparation result."""
        mock_prepare.return_value = {
            'mode': 'prepared',
            'changed_paths': ['reference_templates/default.boot.source.json'],
        }

        result = create_export_pr(
            export_json='{"test": "data"}',
            target_repo='owner/repo',
            github_token=None,
        )

        self.assertEqual(result.get('mode'), 'manual')
        self.assertEqual(result.get('target_repo'), 'owner/repo')
        self.assertIn('prepared_paths', result)

    def test_create_pr_invalid_repo_format(self):
        """Test creating PR with invalid repo format."""
        with self.assertRaises(GitHubPRError) as ctx:
            create_export_pr(
                export_json='{"test": "data"}',
                target_repo='invalid',
                github_token='test_token',
            )
        self.assertIn('Invalid repository format', str(ctx.exception))

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    @patch('routes.import_export.github_pr.prepare_boot_image_update')
    def test_create_pr_branch_exists(self, mock_prepare, mock_get_repo, mock_get_client):
        """Test creating PR when branch already exists."""
        mock_prepare.return_value = {
            'mode': 'prepared',
            'changed_paths': ['reference_templates/default.boot.json'],
        }

        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.default_branch = 'main'
        mock_get_repo.return_value = mock_repo

        # Mock ref and commit
        mock_ref = MagicMock()
        mock_ref.object.sha = 'abc123'
        mock_repo.get_git_ref.return_value = mock_ref

        # Mock branch creation failure (already exists)
        mock_repo.create_git_ref.side_effect = GithubException(422, {'message': 'Reference already exists'}, None)

        # Test
        with self.assertRaises(GitHubPRError) as ctx:
            create_export_pr(
                export_json='{"test": "data"}',
                target_repo='owner/repo',
                github_token='test_token',
                branch_name='existing-branch',
            )
        
        self.assertIn('already exists', str(ctx.exception))

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    @patch('routes.import_export.github_pr.prepare_boot_image_update')
    def test_create_pr_updates_existing_file(self, mock_prepare, mock_get_repo, mock_get_client):
        """Test creating PR when file already exists (update instead of create)."""
        mock_prepare.return_value = {
            'mode': 'prepared',
            'changed_paths': ['reference_templates/default.boot.json'],
        }

        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_repo.default_branch = 'main'
        mock_get_repo.return_value = mock_repo

        # Mock ref and commit
        mock_ref = MagicMock()
        mock_ref.object.sha = 'abc123'
        mock_repo.get_git_ref.return_value = mock_ref

        # Mock file content (exists)
        mock_file = MagicMock()
        mock_file.sha = 'file_sha_123'
        mock_repo.get_contents.return_value = mock_file

        # Mock PR creation
        mock_pr = MagicMock()
        mock_pr.url = 'https://api.github.com/repos/owner/repo/pulls/1'
        mock_pr.number = 1
        mock_pr.html_url = 'https://github.com/owner/repo/pull/1'
        mock_repo.create_pull.return_value = mock_pr

        # Test
        export_json = '{"test": "data"}'
        result = create_export_pr(
            export_json=export_json,
            target_repo='owner/repo',
            github_token='test_token',
        )

        # Assertions
        self.assertEqual(result['number'], 1)
        mock_repo.update_file.assert_called_once()
        mock_repo.create_file.assert_not_called()


class TestFetchPRExportData(unittest.TestCase):
    """Test fetching export data from GitHub PRs."""

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    def test_fetch_pr_success(self, mock_get_repo, mock_get_client):
        """Test successfully fetching PR export data."""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        # Mock PR
        mock_pr = MagicMock()
        mock_pr.head.sha = 'commit_sha_123'
        mock_repo.get_pull.return_value = mock_pr

        # Mock files in PR (either legacy boot image output or a boot source marker)
        mock_file = MagicMock()
        mock_file.filename = 'reference_templates/default.boot.json'
        mock_pr.get_files.return_value = [mock_file]

        # Mock file content
        export_data = {'version': 6, 'test': 'data'}
        mock_content = MagicMock()
        mock_content.decoded_content = json.dumps(export_data).encode('utf-8')
        mock_repo.get_contents.return_value = mock_content

        # Test
        json_data, error = fetch_pr_export_data(
            pr_url='https://github.com/owner/repo/pull/123',
            github_token='test_token',
        )

        # Assertions
        self.assertIsNone(error)
        self.assertIsNotNone(json_data)
        parsed = json.loads(json_data)
        self.assertEqual(parsed['version'], 6)
        self.assertEqual(parsed['test'], 'data')

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    def test_fetch_pr_accepts_boot_source_marker(self, mock_get_repo, mock_get_client):
        """PRs created by the new workflow touch boot source files; import remains legacy."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        mock_pr = MagicMock()
        mock_pr.head.sha = 'commit_sha_123'
        mock_repo.get_pull.return_value = mock_pr

        marker = MagicMock()
        marker.filename = 'reference_templates/default.boot.source.json'
        mock_pr.get_files.return_value = [marker]

        # Legacy file required for import; simulate missing
        mock_repo.get_contents.side_effect = GithubException(404, {'message': 'Not Found'}, None)

        json_data, error = fetch_pr_export_data(
            pr_url='https://github.com/owner/repo/pull/123',
            github_token='test_token',
        )

        self.assertIsNone(json_data)
        self.assertIsNotNone(error)
        self.assertIn('updated boot image inputs', error)

    def test_fetch_pr_invalid_url(self):
        """Test fetching PR with invalid URL."""
        json_data, error = fetch_pr_export_data(
            pr_url='not-a-github-url',
            github_token='test_token',
        )

        self.assertIsNone(json_data)
        self.assertIn('Invalid GitHub PR URL', error)


class TestPrepareBootImageUpdate(unittest.TestCase):
    def test_prepare_boot_image_update_materializes_cids_and_does_not_write_generated_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            ref_dir = base_dir / 'reference_templates'
            (ref_dir / 'aliases').mkdir(parents=True)
            (ref_dir / 'servers' / 'definitions').mkdir(parents=True)
            (base_dir / 'cids').mkdir(parents=True)

            base_boot_source = {
                'version': 6,
                'runtime': '{"python": {"version": "3.11.0"}}',
                'project_files': '{}',
                'aliases': [],
                'servers': [],
                'variables': [
                    {'name': 'templates', 'definition': 'GENERATED:templates.json', 'enabled': True},
                    {'name': 'uis', 'definition': 'GENERATED:uis.json', 'enabled': True},
                ],
            }
            (ref_dir / 'default.boot.source.json').write_text(
                json.dumps(base_boot_source, indent=2),
                encoding='utf-8',
            )
            (ref_dir / 'minimal.boot.source.json').write_text(
                json.dumps(base_boot_source, indent=2),
                encoding='utf-8',
            )
            (ref_dir / 'boot.source.json').write_text(
                json.dumps(base_boot_source, indent=2),
                encoding='utf-8',
            )

            minimal_before = (ref_dir / 'minimal.boot.source.json').read_text(encoding='utf-8')
            boot_before = (ref_dir / 'boot.source.json').read_text(encoding='utf-8')
            (ref_dir / 'templates.source.json').write_text(
                json.dumps({'aliases': {}, 'servers': {}, 'variables': {}, 'secrets': {}, 'uploads': {}}, indent=2),
                encoding='utf-8',
            )
            (ref_dir / 'uis.source.json').write_text(
                json.dumps({'aliases': {}, 'servers': {}, 'variables': {}}, indent=2),
                encoding='utf-8',
            )

            alias_definition = 'x' * 80
            alias_definition_cid = generate_cid(alias_definition.encode('utf-8'))
            aliases_section = [
                {'name': 'test-alias', 'definition_cid': alias_definition_cid, 'enabled': True},
            ]
            aliases_section_json = json.dumps(aliases_section)
            aliases_section_cid = generate_cid(aliases_section_json.encode('utf-8'))

            variables_section = [
                {'name': 'CUSTOM_VAR', 'definition': 'custom', 'enabled': True},
            ]
            variables_section_json = json.dumps(variables_section)
            variables_section_cid = generate_cid(variables_section_json.encode('utf-8'))

            servers_section_json = json.dumps([])
            servers_section_cid = generate_cid(servers_section_json.encode('utf-8'))

            payload = {
                'version': 6,
                'aliases': aliases_section_cid,
                'servers': servers_section_cid,
                'variables': variables_section_cid,
                'cid_values': {
                    aliases_section_cid: aliases_section_json,
                    servers_section_cid: servers_section_json,
                    variables_section_cid: variables_section_json,
                    alias_definition_cid: alias_definition,
                },
            }

            with patch.object(BootImageGenerator, 'generate', return_value={}):
                result = prepare_boot_image_update(
                    export_json=json.dumps(payload),
                    base_dir=base_dir,
                )

            self.assertEqual(result.get('mode'), 'prepared')

            alias_path = ref_dir / 'aliases' / 'test-alias.txt'
            self.assertTrue(alias_path.exists())
            self.assertEqual(alias_path.read_text(encoding='utf-8'), alias_definition)

            cid_path = base_dir / 'cids' / alias_definition_cid
            self.assertTrue(cid_path.exists())
            self.assertEqual(cid_path.read_bytes(), alias_definition.encode('utf-8'))

            # Export PR preparation should not modify minimal or legacy boot sources.
            self.assertEqual((ref_dir / 'minimal.boot.source.json').read_text(encoding='utf-8'), minimal_before)
            self.assertEqual((ref_dir / 'boot.source.json').read_text(encoding='utf-8'), boot_before)

            self.assertFalse((ref_dir / 'templates.json').exists())
            self.assertFalse((ref_dir / 'default.boot.json').exists())

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    def test_fetch_pr_not_found(self, mock_get_repo, mock_get_client):
        """Test fetching non-existent PR."""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        # Mock PR not found
        mock_repo.get_pull.side_effect = GithubException(404, {'message': 'Not Found'}, None)

        # Test
        json_data, error = fetch_pr_export_data(
            pr_url='https://github.com/owner/repo/pull/999',
            github_token='test_token',
        )

        self.assertIsNone(json_data)
        self.assertIn('not found', error)

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    def test_fetch_pr_wrong_file(self, mock_get_repo, mock_get_client):
        """Test fetching PR that doesn't modify the boot image file."""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        # Mock PR
        mock_pr = MagicMock()
        mock_pr.head.sha = 'commit_sha_123'
        mock_repo.get_pull.return_value = mock_pr

        # Mock files in PR (wrong file)
        mock_file = MagicMock()
        mock_file.filename = 'some_other_file.txt'
        mock_pr.get_files.return_value = [mock_file]

        # Test
        json_data, error = fetch_pr_export_data(
            pr_url='https://github.com/owner/repo/pull/123',
            github_token='test_token',
        )

        self.assertIsNone(json_data)
        self.assertIn('does not modify a supported boot image file', error)

    @patch('routes.import_export.github_pr.get_github_client')
    @patch('routes.import_export.github_pr.get_repository')
    def test_fetch_pr_invalid_json(self, mock_get_repo, mock_get_client):
        """Test fetching PR with invalid JSON content."""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        # Mock PR
        mock_pr = MagicMock()
        mock_pr.head.sha = 'commit_sha_123'
        mock_repo.get_pull.return_value = mock_pr

        # Mock files in PR
        mock_file = MagicMock()
        mock_file.filename = 'reference_templates/default.boot.json'
        mock_pr.get_files.return_value = [mock_file]

        # Mock file content with invalid JSON
        mock_content = MagicMock()
        mock_content.decoded_content = b'not valid json {'
        mock_repo.get_contents.return_value = mock_content

        # Test
        json_data, error = fetch_pr_export_data(
            pr_url='https://github.com/owner/repo/pull/123',
            github_token='test_token',
        )

        self.assertIsNone(json_data)
        self.assertIn('invalid JSON', error)


if __name__ == '__main__':
    unittest.main()
