import os



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = '[Conference-UI]'
    MAIL_SENDER = 'Conference-UI Admin <slogan@twilio.com>'
    ADMIN = os.environ.get('ADMIN')
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    AUTHY_KEY = os.environ.get('AUTHY_KEY')
    TWILIO_AUTH_TOKEN=os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_SYNC_SERVICE_SID=os.environ.get('TWILIO_SYNC_SERVICE_SID')
    TWILIO_SYNC_MAP_SID = os.environ.get('TWILIO_SYNC_MAP_SID')
    TWILIO_API_KEY=os.environ.get('TWILIO_API_KEY')
    TWILIO_API_SECRET=os.environ.get('TWILIO_API_SECRET')
    TWILIO_NUMBER=os.environ.get('TWILIO_NUMBER')
    SSL_DISABLE = True

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    
    SQL_ALCHEMY_USERNAME = os.environ.get('SQLALCHEMY_USERNAME')
    SQL_ALCHEMY_PASSWORD = os.environ.get('SQLALCHEMY_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI') or \
                'postgresql://' + SQL_ALCHEMY_USERNAME + ':' + SQL_ALCHEMY_PASSWORD + '@localhost/' +  'conf_data_dev'
    SERVER_NAME = os.environ.get('SERVER_NAME')

class TestingConfig(Config):
    TESTING = True
    SQL_ALCHEMY_USERNAME = os.environ.get('SQLALCHEMY_USERNAME')
    SQL_ALCHEMY_PASSWORD = os.environ.get('SQLALCHEMY_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'postgresql://' + SQL_ALCHEMY_USERNAME + ':' + SQL_ALCHEMY_PASSWORD + '@localhost/' +  'conf_data_test'


class ProductionConfig(Config):
    SQL_ALCHEMY_USERNAME = os.environ.get('SQLALCHEMY_USERNAME')
    SQL_ALCHEMY_PASSWORD = os.environ.get('SQLALCHEMY_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://' + SQL_ALCHEMY_USERNAME + ':' + SQL_ALCHEMY_PASSWORD + '@localhost/' +  'conference_data'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        #email errors to administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.MAIL_SENDER,
            toaddrs=[cls.ADMIN],
            subject=cls.MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        #log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'default': DevelopmentConfig

}
