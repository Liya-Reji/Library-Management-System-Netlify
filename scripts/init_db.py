"""
Safe database initialization script.
Creates all database tables defined in SQLAlchemy models if they do not exist.
Does not drop or delete existing data.
"""
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import db

def initialize_database():
    app = create_app()
    with app.app_context():
        print(f"Connecting to database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        print("Success: Database schema and tables verified/created successfully.")

if __name__ == "__main__":
    initialize_database()
