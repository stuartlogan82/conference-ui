import unittest
from app import create_app, db
from app.models import User

class UserModelTestCase(unittest.TestCase):
    def test_setters(self):
        u = User(password='cat', 
                twilio_account_sid='ACfd0573f9f976b99746c693947axxxxxx',
                twilio_auth_token='fe4fdcdb09e234bfb63a4091f8xxxxxx')
        self.assertTrue(u.password_hash is not None)
        self.assertTrue(u.twilio_account_sid_hash is not None)
        self.assertTrue(u.twilio_auth_token_hash is not None)

    def test_no_getters(self):
        u = User(password='cat',
                 twilio_account_sid='ACfd0573f9f976b99746c693947axxxxxx',
                 twilio_auth_token='fe4fdcdb09e234bfb63a4091f8xxxxxx')
        with self.assertRaises(AttributeError):
            u.password
            u.twilio_account_sid
            u.twilio_auth_token

    def test_password_verification(self):
        u = User(password='cat',
                 twilio_account_sid='ACfd0573f9f976b99746c693947axxxxxx',
                 twilio_auth_token='fe4fdcdb09e234bfb63a4091f8xxxxxx')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))
        self.assertTrue(u.verify_twilio_account_sid(
            'ACfd0573f9f976b99746c693947axxxxxx'))
        self.assertFalse(u.verify_twilio_account_sid('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'))
        self.assertTrue(u.verify_twilio_auth_token(
            'fe4fdcdb09e234bfb63a4091f8xxxxxx'))
        self.assertFalse(u.verify_twilio_auth_token(
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'))

    def test_salts_are_random(self):
        u = User(password = 'cat',
                twilio_account_sid = 'ACfd0573f9f976b99746c693947axxxxxx',
                twilio_auth_token = 'fe4fdcdb09e234bfb63a4091f8xxxxxx')
        u2 = User(password='cat',
                  twilio_account_sid='ACfd0573f9f976b99746c693947axxxxxx',
                  twilio_auth_token='fe4fdcdb09e234bfb63a4091f8xxxxxx')
        self.assertTrue(u.password_hash != u2.password_hash)
        self.assertTrue(u.twilio_account_sid_hash !=
                        u2.twilio_account_sid_hash)
        self.assertTrue(u.twilio_auth_token_hash != u2.twilio_auth_token_hash)
