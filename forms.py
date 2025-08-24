from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import BooleanField, SelectField, SubmitField, StringField, TextAreaField
from wtforms.validators import DataRequired, Optional

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
