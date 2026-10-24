import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_database_url():
    """Normalize database URL for SQLAlchemy (Render uses postgres:// which must be postgresql://)."""
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        # Default to local SQLite database in instance directory
        os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
        return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'library.db')}"
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-123456789")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    DEFAULT_LOAN_DAYS = int(os.getenv("DEFAULT_LOAN_DAYS", 14))

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    SECRET_KEY = "test-secret-key"

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_database_url()
    # In production with HTTPS, enable secure cookies
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() in ("true", "1", "yes")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
