import os
from app import create_app, database_exists
from models import db

# Create instance directory with absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

def initialize_database():
    """Initialize database only if tables don't exist."""
    app = create_app()
    with app.app_context():
        if not database_exists():
            db.create_all()
            print("Database tables created successfully")
        else:
            print("Database already exists, skipping initialization")

if __name__ == "__main__":
    initialize_database()