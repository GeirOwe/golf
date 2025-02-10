import os
from app import app, db

# Create instance directory with absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

def init_database():
    # Ensure instance directory exists
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    
    # Set directory permissions
    os.chmod(INSTANCE_DIR, 0o777)
    
    # Initialize database
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()