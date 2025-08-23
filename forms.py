from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=4, max=25, message='Username must be between 4 and 25 characters.')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters.')
    ])
    password2 = PasswordField('Repeat Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class PaymentForm(FlaskForm):
    plan = SelectField('Plan', choices=[
        ('basic', 'Basic Plan - $9.99/month'),
        ('premium', 'Premium Plan - $19.99/month'),
        ('enterprise', 'Enterprise Plan - $49.99/month')
    ], validators=[DataRequired()])
    submit = SubmitField('Subscribe')

class TermsAcceptanceForm(FlaskForm):
    accept_terms = BooleanField('I accept the current Terms and Conditions', validators=[DataRequired()])
    submit = SubmitField('Accept Terms')
