import os
import warnings
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///fbs.db')

# Render provides DATABASE_URL with postgres:// but SQLAlchemy requires postgresql://
if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

if 'sqlite' in (SQLALCHEMY_DATABASE_URI or ''):
    warnings.warn(
        '\n*** WARNING: Using SQLite — data WILL BE LOST on platforms with '
        'ephemeral filesystems (Render, Heroku, etc.).\n'
        '*** Set DATABASE_URL to a PostgreSQL connection string for production.\n',
        stacklevel=1,
    )
WTF_CSRF_ENABLED= True

# Mail
MAIL_SERVER = os.getenv('MAIL_SERVER',  'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME= os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD= os.getenv('MAIL_PASSWORD', '')
MAIL_SUPPRESS_SEND= os.getenv('MAIL_SUPPRESS_SEND', 'false').lower() == 'true'
MAIL_DEFAULT_SENDER= (
    os.getenv('MAIL_DISPLAY_NAME',   'DUT Campus Booking System'),
    os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', '')),
)

# Google reCAPTCHA v2
RECAPTCHA_SITE_KEY= os.getenv('RECAPTCHA_SITE_KEY',   '')
RECAPTCHA_SECRET_KEY= os.getenv('RECAPTCHA_SECRET_KEY', '')

# Microsoft OAuth
MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID',     '')
MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET', '')
MICROSOFT_TENANT_ID = os.getenv('MICROSOFT_TENANT_ID',     'common')

# File uploads
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads/avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# PayFast
PAYFAST_MERCHANT_ID = os.getenv('PAYFAST_MERCHANT_ID')
PAYFAST_MERCHANT_KEY = os.getenv('PAYFAST_MERCHANT_KEY')
PAYFAST_URL= os.getenv('PAYFAST_URL')

# Session security
SESSION_COOKIE_HTTPONLY= True
SESSION_COOKIE_SAMESITE='Lax'
PERMANENT_SESSION_LIFETIME= 3600
