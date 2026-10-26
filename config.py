import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def normalize_database_url(raw_url):
    """
    Normalize database URL for SQLAlchemy.
    Render uses postgres:// which SQLAlchemy 1.4+ requires to be postgresql://.
    """
    if not raw_url:
        return None
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def get_database_url(is_production=False):
    """
    Fetch and validate the database URL.
    In production, fails fast if DATABASE_URL is missing to prevent silent fallback to SQLite.
    In development/testing, falls back to local SQLite.
    """
    raw_url = os.getenv("DATABASE_URL")
    normalized = normalize_database_url(raw_url)
    if normalized:
        return normalized

    if is_production:
        raise RuntimeError(
            "CRITICAL CONFIGURATION ERROR: DATABASE_URL environment variable is required in production. "
            "Set DATABASE_URL to your PostgreSQL connection string in the Render Dashboard to connect to your database."
        )

    # Local development fallback to SQLite
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'library.db')}"

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-123456789")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    DEFAULT_LOAN_DAYS = int(os.getenv("DEFAULT_LOAN_DAYS", 14))

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_database_url(is_production=False)
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
    # If DATABASE_URL is available at import time, normalize it;
    # otherwise create_app will validate and enforce it dynamically.
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    # In production with HTTPS, enable secure cookies
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() in ("true", "1", "yes")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
