"""
Safe database initialization script.
Creates all database tables defined in SQLAlchemy models if they do not exist.
Does not drop or delete existing data.
Credentials and passwords are masked to prevent leaking in build logs.
"""
import sys
import os
from urllib.parse import urlparse

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import db

def mask_connection_url(url):
    """Mask password in connection URL for safe logging."""
    if not url:
        return "None"
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            return parsed._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "Configured Database URL"

def initialize_database():
    app = create_app()
    with app.app_context():
        masked_url = mask_connection_url(app.config.get("SQLALCHEMY_DATABASE_URI"))
        print(f"[*] Target database: {masked_url}")
        db.create_all()
        print("[+] Success: Database schema and tables verified/created successfully.")

if __name__ == "__main__":
    initialize_database()
