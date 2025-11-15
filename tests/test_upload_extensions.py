import io
import unittest
from unittest.mock import Mock

from app import create_app, db
from cid_presenter import format_cid
from cid_utils import CID_LENGTH, CID_MIN_LENGTH, generate_cid, process_file_upload
from models import Variable


class TestUploadExtensions(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
        })

        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_process_file_upload_returns_filename(self):
        """Test that process_file_upload returns both content and filename"""
        form = Mock()
        mock_file = Mock()
        mock_file.filename = 'test_document.pdf'
        mock_file.read.return_value = b'test file content'
        form.file.data = mock_file

        content, filename = process_file_upload(form)

        self.assertEqual(content, b'test file content')
        self.assertEqual(filename, 'test_document.pdf')

    def test_process_file_upload_handles_no_filename(self):
        """Test that process_file_upload handles files without filename"""
        form = Mock()
        mock_file = Mock()
        mock_file.filename = None
        mock_file.read.return_value = b'test file content'
        form.file.data = mock_file

        content, filename = process_file_upload(form)

        self.assertEqual(content, b'test file content')
        self.assertEqual(filename, 'upload')

    def test_upload_text_gets_txt_extension(self):
        """Test that pasted text uploads get .txt extension in view URL"""
        with self.app.app_context():
            response = self.client.post('/upload', data={
                'upload_type': 'text',
                'text_content': 'This is some test text content',
                'submit': 'Upload'
            }, follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upload Successful', response.data)
        self.assertIn(b'.txt', response.data)

    def test_upload_file_preserves_original_extension(self):
        """Test that file uploads preserve their original extension"""
        with self.app.app_context():
            file_data = io.BytesIO(b'PDF file content')
            file_data.name = 'document.pdf'

            response = self.client.post('/upload', data={
                'upload_type': 'file',
                'file': (file_data, 'document.pdf'),
                'submit': 'Upload'
            }, follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upload Successful', response.data)
        self.assertIn(b'.pdf', response.data)

    def test_upload_file_handles_no_extension(self):
        """Test that file uploads without extension don't break"""
        with self.app.app_context():
            file_data = io.BytesIO(b'File content without extension')
            file_data.name = 'document'

            response = self.client.post('/upload', data={
                'upload_type': 'file',
                'file': (file_data, 'document'),
                'submit': 'Upload'
            }, follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upload Successful', response.data)

        response_text = response.data.decode('utf-8')
        cid_pattern = rf'/[A-Za-z0-9_-]{{{CID_MIN_LENGTH},{CID_LENGTH}}}(?!\.)'
        self.assertRegex(response_text, cid_pattern)

    def test_upload_success_includes_variable_assignment_form(self):
        """Upload success page should render variable assignment controls."""

        with self.app.app_context():
            db.session.add(
                Variable(name='existing-var', definition='/old-cid')
            )
            db.session.commit()

            response = self.client.post('/upload', data={
                'upload_type': 'text',
                'text_content': 'variable assignment preview',
                'submit': 'Upload'
            }, follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('Assign this CID to a Variable', page)
        self.assertIn('existing-var', page)
        self.assertIn('name="cid"', page)

    def test_assign_cid_creates_new_variable(self):
        """Assigning a CID should create a new variable."""

        content_text = 'new variable content'

        with self.app.app_context():
            upload_response = self.client.post('/upload', data={
                'upload_type': 'text',
                'text_content': content_text,
                'submit': 'Upload'
            }, follow_redirects=False)

        self.assertEqual(upload_response.status_code, 200)

        cid_value = format_cid(generate_cid(content_text.encode('utf-8')))

        assign_response = self.client.post('/upload/assign-variable', data={
            'cid': cid_value,
            'variable_name': 'NEW_ASSIGN',
            'view_url_extension': 'txt',
            'filename': '',
            'detected_mime_type': 'text/plain',
        })

        self.assertEqual(assign_response.status_code, 200)
        assign_page = assign_response.get_data(as_text=True)
        self.assertIn('NEW_ASSIGN', assign_page)
        self.assertIn('currently assigned', assign_page)

        with self.app.app_context():
            created = Variable.query.filter_by(name='NEW_ASSIGN').first()
            self.assertIsNotNone(created)
            self.assertEqual(created.definition, f'/{cid_value}')

    def test_assign_cid_updates_existing_variable(self):
        """Assigning a CID should update an existing variable definition."""

        with self.app.app_context():
            db.session.add(
                Variable(name='STATUS_PAGE', definition='/old-definition')
            )
            db.session.commit()

        updated_text = 'updated variable definition via cid'

        with self.app.app_context():
            upload_response = self.client.post('/upload', data={
                'upload_type': 'text',
                'text_content': updated_text,
                'submit': 'Upload'
            }, follow_redirects=False)

        self.assertEqual(upload_response.status_code, 200)

        cid_value = format_cid(generate_cid(updated_text.encode('utf-8')))

        assign_response = self.client.post('/upload/assign-variable', data={
            'cid': cid_value,
            'variable_name': 'STATUS_PAGE',
            'view_url_extension': 'txt',
            'filename': '',
            'detected_mime_type': 'text/plain',
        })

        self.assertEqual(assign_response.status_code, 200)
        page = assign_response.get_data(as_text=True)
        self.assertIn('STATUS_PAGE', page)

        with self.app.app_context():
            refreshed = Variable.query.filter_by(name='STATUS_PAGE').one()
            self.assertEqual(refreshed.definition, f'/{cid_value}')


if __name__ == '__main__':
    unittest.main()
