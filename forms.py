from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, SelectField, SubmitField, StringField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Optional, Regexp, ValidationError
from urllib.parse import urlsplit
import re

from alias_matching import PatternError, evaluate_test_strings, normalise_pattern


def _strip_filter(value):
    return value.strip() if isinstance(value, str) else value

class PaymentForm(FlaskForm):
    plan = SelectField('Plan', choices=[
        ('free', 'Free Plan - $0/year'),
        ('annual', 'Annual Plan - $50/year')
    ], validators=[DataRequired()])
    submit = SubmitField('Subscribe')

class TermsAcceptanceForm(FlaskForm):
    accept_terms = BooleanField('I accept the current Terms and Conditions', validators=[DataRequired()])
    submit = SubmitField('Accept Terms')

class FileUploadForm(FlaskForm):
    upload_type = RadioField('Upload Method', choices=[
        ('file', 'Upload File'),
        ('text', 'Paste Text'),
        ('url', 'Download from URL')
    ], default='file', validators=[DataRequired()])
    file = FileField('Choose File', validators=[Optional()])
    text_content = TextAreaField('Text Content', validators=[Optional()], render_kw={'rows': 10, 'placeholder': 'Paste your text content here...'})
    url = StringField('URL', validators=[Optional()], render_kw={'placeholder': 'https://example.com/file.pdf'})
    submit = SubmitField('Upload')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        if self.upload_type.data == 'file':
            if not self.file.data:
                self.file.errors.append('File is required when using file upload.')
                return False
        elif self.upload_type.data == 'text':
            if not self.text_content.data or not self.text_content.data.strip():
                self.text_content.errors.append('Text content is required when using text upload.')
                return False
        elif self.upload_type.data == 'url':
            if not self.url.data or not self.url.data.strip():
                self.url.errors.append('URL is required when using URL upload.')
                return False
            # Basic URL validation
            url = self.url.data.strip()
            if not (url.startswith('http://') or url.startswith('https://')):
                self.url.errors.append('URL must start with http:// or https://')
                return False

        return True


class EditCidForm(FlaskForm):
    text_content = TextAreaField(
        'CID Content',
        validators=[DataRequired()],
        render_kw={'rows': 15, 'placeholder': 'Update the CID content here...'},
    )
    alias_name = StringField(
        'Alias Name (optional)',
        validators=[
            Optional(),
            Regexp(
                r'^[a-zA-Z0-9._-]+$',
                message='Alias name can only contain letters, numbers, dots, hyphens, and underscores',
            ),
        ],
        filters=[_strip_filter],
    )
    submit = SubmitField('Save Changes')

class InvitationForm(FlaskForm):
    email = StringField('Email (optional)', validators=[Optional()])
    submit = SubmitField('Create Invitation')

class InvitationCodeForm(FlaskForm):
    invitation_code = StringField('Invitation Code', validators=[DataRequired()])
    submit = SubmitField('Verify Invitation')

class ServerForm(FlaskForm):
    name = StringField('Server Name', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9._-]+$', message='Server name can only contain letters, numbers, dots, hyphens, and underscores')
    ])
    definition = TextAreaField('Server Definition', validators=[DataRequired()], render_kw={'rows': 15})
    submit = SubmitField('Save Server')

    def validate_name(self, field):
        # Additional validation to ensure URL safety
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError('Server name contains invalid characters for URLs')

class VariableForm(FlaskForm):
    name = StringField('Variable Name', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9._-]+$', message='Variable name can only contain letters, numbers, dots, hyphens, and underscores')
    ])
    definition = TextAreaField('Variable Definition', validators=[DataRequired()], render_kw={'rows': 15})
    submit = SubmitField('Save Variable')

    def validate_name(self, field):
        # Additional validation to ensure URL safety
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError('Variable name contains invalid characters for URLs')

class AliasForm(FlaskForm):
    name = StringField(
        'Alias Name',
        validators=[
            DataRequired(),
            Regexp(
                r'^[a-zA-Z0-9._-]+$',
                message='Alias name can only contain letters, numbers, dots, hyphens, and underscores'
            ),
        ],
        filters=[_strip_filter],
    )
    target_path = StringField(
        'Target Path',
        validators=[DataRequired()],
        filters=[_strip_filter],
        render_kw={'placeholder': '/cid123 or /path?query=1'},
    )
    match_type = RadioField(
        'Match Type',
        choices=[
            ('literal', 'Literal'),
            ('glob', 'Glob'),
            ('regex', 'Regular Expression'),
            ('flask', 'Flask Route'),
        ],
        default='literal',
        validators=[DataRequired()],
    )
    match_pattern = StringField(
        'Match Pattern',
        filters=[_strip_filter],
        render_kw={'placeholder': '/latest or /users/<username>'},
    )
    ignore_case = BooleanField('Ignore Case')
    test_strings = TextAreaField(
        'Test Strings',
        render_kw={'rows': 4, 'placeholder': '/users/alice'},
    )
    submit = SubmitField('Save Alias')
    test_pattern = SubmitField('Test Pattern')

    def validate_target_path(self, field):
        target = field.data
        if not target:
            raise ValidationError('Target path is required.')
        if target.startswith('//'):
            raise ValidationError('Target path must stay within this application.')

        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            raise ValidationError('Target path must stay within this application.')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        match_type = (self.match_type.data or 'literal').lower()

        if match_type == 'literal':
            self.match_pattern.data = self.name.data
        try:
            normalised = normalise_pattern(match_type, self.match_pattern.data, self.name.data)
        except PatternError as exc:
            self.match_pattern.errors.append(str(exc))
            return False

        self.match_pattern.data = normalised
        return True

    def evaluated_tests(self):
        if not self.match_pattern.data:
            return []
        raw_values = (self.test_strings.data or '').splitlines()
        return evaluate_test_strings(
            self.match_type.data,
            self.match_pattern.data,
            raw_values,
            ignore_case=bool(self.ignore_case.data),
        )

class SecretForm(FlaskForm):
    name = StringField('Secret Name', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9._-]+$', message='Secret name can only contain letters, numbers, dots, hyphens, and underscores')
    ])
    definition = TextAreaField('Secret Definition', validators=[DataRequired()], render_kw={'rows': 15})
    submit = SubmitField('Save Secret')

    def validate_name(self, field):
        # Additional validation to ensure URL safety
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError('Secret name contains invalid characters for URLs')


class ExportForm(FlaskForm):
    include_aliases = BooleanField('Aliases')
    include_servers = BooleanField('Servers')
    include_variables = BooleanField('Variables')
    include_secrets = BooleanField('Secrets')
    include_history = BooleanField('Change History')
    secret_key = StringField(
        'Secret Encryption Key',
        validators=[Optional()],
        render_kw={'placeholder': 'Required when exporting secrets'},
    )
    submit = SubmitField('Generate JSON Export')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        if not any([
            self.include_aliases.data,
            self.include_servers.data,
            self.include_variables.data,
            self.include_secrets.data,
            self.include_history.data,
        ]):
            message = 'Select at least one data type to export.'
            self.include_aliases.errors.append(message)
            return False

        if self.include_secrets.data and not (self.secret_key.data and self.secret_key.data.strip()):
            self.secret_key.errors.append('Encryption key is required when exporting secrets.')
            return False

        return True


class ImportForm(FlaskForm):
    import_source = RadioField(
        'Import Method',
        choices=[
            ('file', 'Upload JSON File'),
            ('text', 'Paste JSON Text'),
            ('url', 'Load JSON from URL'),
        ],
        default='file',
        validators=[DataRequired()],
    )
    import_file = FileField('JSON File', validators=[Optional()])
    import_text = TextAreaField(
        'JSON Text',
        validators=[Optional()],
        render_kw={'rows': 10, 'placeholder': '{"aliases": []}'},
    )
    import_url = StringField(
        'JSON URL',
        validators=[Optional()],
        render_kw={'placeholder': 'https://example.com/export.json'},
    )
    include_aliases = BooleanField('Aliases')
    include_servers = BooleanField('Servers')
    include_variables = BooleanField('Variables')
    include_secrets = BooleanField('Secrets')
    include_history = BooleanField('Change History')
    secret_key = StringField(
        'Secret Decryption Key',
        validators=[Optional()],
        render_kw={'placeholder': 'Required when importing secrets'},
    )
    submit = SubmitField('Import Data')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        if not any([
            self.include_aliases.data,
            self.include_servers.data,
            self.include_variables.data,
            self.include_secrets.data,
            self.include_history.data,
        ]):
            message = 'Select at least one data type to import.'
            self.include_aliases.errors.append(message)
            return False

        source = self.import_source.data
        if source == 'file':
            file_storage = self.import_file.data
            if not getattr(file_storage, 'filename', None):
                self.import_file.errors.append('Choose a JSON file to upload.')
                return False
        elif source == 'text':
            if not (self.import_text.data and self.import_text.data.strip()):
                self.import_text.errors.append('Paste JSON content to import.')
                return False
        elif source == 'url':
            if not (self.import_url.data and self.import_url.data.strip()):
                self.import_url.errors.append('Provide a URL to download JSON from.')
                return False

        if self.include_secrets.data and not (self.secret_key.data and self.secret_key.data.strip()):
            self.secret_key.errors.append('Decryption key is required when importing secrets.')
            return False

        return True
