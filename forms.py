from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, SelectField, SubmitField, StringField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Optional, Regexp, ValidationError
from urllib.parse import urlsplit
import re


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
    submit = SubmitField('Save Alias')

    def validate_target_path(self, field):
        target = field.data
        if not target:
            raise ValidationError('Target path is required.')
        if target.startswith('//'):
            raise ValidationError('Target path must stay within this application.')

        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            raise ValidationError('Target path must stay within this application.')

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
