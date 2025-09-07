from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import BooleanField, SelectField, SubmitField, StringField, TextAreaField
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
    file = FileField('Choose File', validators=[FileRequired()])
    title = StringField('Title (optional)', validators=[Optional()])
    description = TextAreaField('Description (optional)', validators=[Optional()])
    submit = SubmitField('Upload File')

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
