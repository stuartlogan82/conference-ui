from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User
from ..twilio import twilio_lookup

class LoginForm(FlaskForm):
    email = StringField('E-Mail', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1, 64), Email()])
    first_name = StringField('First Name', validators=[
                            Required(), Length(1, 64), 
                            Regexp('[A-Za-z][A-Za-z\-\']*$', 0,
                                    'Names must have only letters, apostrophes and hyphens')])
    last_name = StringField('Last Name', validators=[
                            Required(), Length(1, 64),
                            Regexp('[A-Za-z][A-Za-z]*$', 0,
                                   'Names must have only letters, apostrophes and hyphens')])
    password = PasswordField('Password', validators=[
                            Required(), 
                            EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[Required()])
    country_code = SelectField('Country',
                            choices=[('+44', 'UK +44'), ('+1', 'US +1')], validators=[Required()])
    phone_number = StringField('Phone Number', validators=[Required(),Length(1,15), 
                            Regexp('[0-9]*$', 0, 'Must be numbers only')])
    twilio_sid = StringField('Twilio Account SID', validators=[
                            Required(), Length(30, 40),
                            Regexp('[A-Za-z][A-Za-z0-9]*$', 0,
                                   'Not a valid Account SID')])
    twilio_token = StringField('Twilio Auth Token', validators=[
                            Required(), Length(15, 40),
                            Regexp('[A-Za-z0-9]*$', 0,
                                   'Not a valid Auth Token')])
    """twilioPhoneNumber = StringField('Phone Number', validators=[Required(), Length(1,15), 
                            Regexp('[\+][0-9]*$', 0, 'Must be numbers only')])"""
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered!')

