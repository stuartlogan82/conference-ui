from . import db
from flask import current_app
from flask_login import UserMixin
from . import login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from authy.api import AuthyApiClient

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Participant(db.Model):
    __tablename__ = 'participants'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(32))
    duration = db.Column(db.Integer)
    direction = db.Column(db.String(16))
    call_sid = db.Column(db.String(64), unique=True, index=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))

    def __repr__(self):
        return '<Conference %r>' % self.call_sid


class Conference(db.Model):
    __tablename__ = 'conferences'
    id = db.Column(db.Integer, primary_key=True)
    call_sid = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64))
    account_sid = db.Column(db.String(64))
    date_created = db.Column(db.String(64))
    participants = db.relationship('Participant', backref='conference')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Conference %r>' % self.call_sid


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), unique=True, index=True)
    last_name = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    country_code = db.Column(db.String(16))
    phone = db.Column(db.String(32), unique=True)
    conferences = db.relationship('Conference', backref='users')
    password_hash = db.Column(db.String(128))
    twilio_account_sid_hash = db.Column(db.String(128))
    twilio_auth_token_hash = db.Column(db.String(128))
    phone_number_confirmed = db.Column(db.Boolean, default=False)
    authy_user_id = db.Column(db.String)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def twilio_account_sid(self):
        raise AttributeError('twilio_account_sid is not a readable attribute')

    @twilio_account_sid.setter
    def twilio_account_sid(self, twilio_account_sid):
        self.twilio_account_sid_hash = generate_password_hash(twilio_account_sid)

    def verify_twilio_account_sid(self, twilio_account_sid):
        return check_password_hash(self.twilio_account_sid_hash, twilio_account_sid)

    @property
    def twilio_auth_token(self):
        raise AttributeError('twilio_auth_token is not a readable attribute')

    @twilio_auth_token.setter
    def twilio_auth_token(self, twilio_auth_token):
        self.twilio_auth_token_hash = generate_password_hash(twilio_auth_token)


    def verify_twilio_auth_token(self, twilio_auth_token):
        return check_password_hash(self.twilio_auth_token_hash, twilio_auth_token)


    def generate_confirmation_code(self):
        authy_api = AuthyApiClient(current_app.config['AUTHY_KEY'])
        request = authy_api.phones.verification_start(self.phone, self.country_code, via='sms')
        return request.content


    def check_confirmation_code(self, code):
        authy_api = AuthyApiClient(current_app.config['AUTHY_KEY'])
        check = authy_api.phones.verification_check(
            self.phone, self.country_code, code)
        if check.ok():
            self.phone_number_confirmed = True
            db.session.add(self)
            return True
        else:
            return False

        
    def create_authy_user(self):
        authy_api = AuthyApiClient(current_app.config['AUTHY_KEY'])
        user = authy_api.users.create(self.email, self.phone, self.country_code)
        if user.ok():
            self.authy_user_id = user.id
            db.session.add(self)
            return True
        else:
            print(user.errors())
            return False


    def generate_2fa(self):
        authy_api = AuthyApiClient(current_app.config['AUTHY_KEY'])
        request = authy_api.users.request_sms(self.authy_user_id)
        return request.content


    def check_2fa(self, code):
        authy_api = AuthyApiClient(current_app.config['AUTHY_KEY'])
        check = authy_api.tokens.verify(self.authy_user_id, code)
        if check.ok():
            return True
        else:
            return False


    def __repr__(self):
        return '<User %r>' % self.username
