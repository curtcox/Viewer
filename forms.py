from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import BooleanField, SelectField, SubmitField, StringField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Optional, Regexp, ValidationError
import re

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
        ('text', 'Paste Text')
    ], default='file', validators=[DataRequired()])
    file = FileField('Choose File', validators=[Optional()])
    text_content = TextAreaField('Text Content', validators=[Optional()], render_kw={'rows': 10, 'placeholder': 'Paste your text content here...'})
    filename = StringField('Filename (for text uploads)', validators=[Optional()], render_kw={'placeholder': 'e.g., document.txt'})
    content_type = StringField('Content Type', validators=[Optional()], render_kw={'placeholder': 'Auto-detected based on filename and content'})
    title = StringField('Title (optional)', validators=[Optional()])
    description = TextAreaField('Description (optional)', validators=[Optional()])
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
            if not self.filename.data or not self.filename.data.strip():
                self.filename.errors.append('Filename is required when using text upload.')
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
