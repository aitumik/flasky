import os

base_dir = os.path.abspath(os.path.dirname(__file__))


class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hardtoguessstring'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    BLOGGING_MAIL_PREFIX = '[Blogging]'
    BLOGGING_ADMIN_EMAIL = os.environ.get('MAIL_ADMIN')
    BLOGGING_MAIL_SENDER = os.environ.get('MAIL_SENDER')
    BLOGGING_ADMIN =  os.environ.get('MAIL_ADMIN')
    BLOGGING_MAIL_SUBJECT_PREFIX = "[Blogging]"
    BLOGGING_POSTS_PER_PAGE = 5
    BLOGGING_COMMENTS_PER_PAGE = 5

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):

    DEBUG = True
    MAIL_SERVER = 'smtp.sendgrid.net'
    MAIL_PORT = 587
    #MAIL_USE_SSL = True
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = "sqlite:////" + os.path.join(base_dir,'data-dev.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    #SQLALCHEMY_ECHO = True

class TestingConfig(Config):

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:////" + os.path.join(base_dir,'data-test.sqlite')
    #SQLALCHEMY_DATABASE_URI = "mysql+pymysql://cbuser:cbpass@localhost:3306/cookbook"
    SQLALCHEMY_TRACK_MODIFICATIONS = True


class ProductionConfig(Config):

    SQLALCHEMY_DATABASE_URI = "sqlite:////" + os.path.join(base_dir,'data.sqlite')



config = {
'development': DevelopmentConfig,
'testing': TestingConfig,
'production': ProductionConfig,
'default': DevelopmentConfig
}
