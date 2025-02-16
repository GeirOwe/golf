# Golf Player Management Application

## Overview
A Flask web application for managing golf players with in-memory storage and Render.com deployment.

## Local Development Setup

### Prerequisites
- Python 3.9+
- macOS 10.15+
- Visual Studio Code
- Git

### Initial Setup

1. **Create Local Project**
```bash
# Create project directory
mkdir ~/Documents/GitHub/golf
cd ~/Documents/GitHub/golf
```

2. **Initialize Git and Create Project Structure**
```bash
# Initialize git repository
git init

# Create project files
touch app.py models.py requirements.txt
mkdir templates
touch templates/base.html templates/home.html templates/list_players.html templates.register_player.html
```

3. **Set Up Python Environment**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install Flask==3.0.2 gunicorn==23.0.0

# Create requirements.txt
pip freeze > requirements.txt
```

4. **Connect to GitHub**
```bash
# Create .gitignore
echo "venv/" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Initial commit
git add .
git commit -m "Initial commit"

# Connect to GitHub repository
git remote add origin https://github.com/yourusername/golf.git
git branch -M main
git push -u origin main
```

### Project Structure
```plaintext
golf/
├── .git/               # Git repository
├── .gitignore         # Git ignore file
├── app.py             # Flask application & routes
├── models.py          # Player model with in-memory storage
├── requirements.txt   # Project dependencies
├── venv/              # Virtual environment (not in git)
└── templates/         # HTML templates
    ├── base.html     # Base template with styling
    ├── home.html     # Home page
    ├── list_players.html    # Player listing
    └── register_player.html # Registration form
```

## Application Components

### Flask Application (`app.py`)
```python
# Main routes:
@app.route("/")                    # Home page
@app.route("/register")            # Display registration form
@app.route("/add_player")          # Process new player
@app.route("/players")             # List all players
@app.route("/player/<id>/delete")  # Delete player
```

### Player Model (`models.py`)
```python
class Player:
    players = []  # In-memory storage
    
    @classmethod
    def get_all(cls):
        return cls.players
    
    @classmethod
    def get_by_id(cls, player_id):
        return next((p for p in cls.players if p.id == player_id), None)
```

### Key Features
1. **In-Memory Storage**
   - Data stored in Python list
   - Resets on application restart
   - Simple but non-persistent

2. **@classmethod Implementation**
   - Efficient data access
   - No instance creation needed
   - Clean code structure

3. **RESTful Routes**
   - Clear URL structure
   - Proper HTTP methods
   - Redirects after actions

## Deployment to Render.com

### Requirements
```python
# filepath: requirements.txt
Flask==3.0.2
gunicorn==23.0.0
```

### Render Configuration
```yaml
# filepath: render.yaml
services:
  - type: web
    name: golf-app
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
      - key: FLASK_ENV
        value: production
```

### Deployment Steps
1. Push code to GitHub
2. Connect to Render.com
3. Create new Web Service
4. Configure environment:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

### Render.com Notes
- Free tier limitations:
  - Instance spins down with inactivity
  - ~50 second cold start
  - Non-persistent storage
- URL: https://golf-app-w497.onrender.com
- Dashboard: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0

## Local Development

### Running the Application
```bash
# Start development server
python app.py

# Access application
open http://localhost:5000
```

### Development Notes
- Debug mode enabled locally
- Auto-reload on code changes
- In-memory data resets on restart

## Testing
```bash
# Install pytest (when needed)
pip install pytest

# Run tests (when implemented)
pytest
```

## Future Improvements
1. Add persistent storage
2. Implement user authentication
3. Add score tracking
4. Improve error handling
5. Add input validation

# PostgreSQL Setup and Commands

## Local Installation (macOS)

```bash
# Install PostgreSQL using Homebrew
brew install postgresql@16

# Start PostgreSQL service
brew services start postgresql@16

# Add to PATH (add to ~/.zshrc)
export PATH="/usr/local/opt/postgresql@16/bin:$PATH"
```

## Database Commands

### Basic Database Management
```bash
# Create database
createdb golf_dev

# Delete database
dropdb golf_dev

# List all databases
psql -l

# Connect to database
psql golf_dev
```

### Useful PSQL Commands
```sql
-- List all tables
\dt

-- Describe table
\d players

-- List all users
\du

-- Exit psql
\q

-- Clear screen
\! clear
```

### Common SQL Queries
```sql
-- View all players
SELECT * FROM players;

-- Delete all players
DELETE FROM players;

-- Reset auto-increment
ALTER SEQUENCE players_id_seq RESTART WITH 1;

-- Count players
SELECT COUNT(*) FROM players;
```

## Database Connection

### Local Development
```bash
# Environment variables for local development
DATABASE_URL=postgresql://localhost/golf_dev
FLASK_ENV=development
```

### Render.com Connection
- Database Name: golf_db_jn45
- Connection string format: 
  `postgresql://user:password@host:port/database`
- Connection managed through Render.com environment variables

## Troubleshooting

### Service Status
```bash
# Check PostgreSQL service status
brew services list

# Restart PostgreSQL service
brew services restart postgresql@16

# Stop PostgreSQL service
brew services stop postgresql@16
```

### Common Issues
1. **Connection refused**
   ```bash
   # Start PostgreSQL service
   brew services start postgresql@16
   ```

2. **Database doesn't exist**
   ```bash
   # Create database
   createdb golf_dev
   ```

3. **Permission denied**
   ```bash
   # Create superuser
   createuser -s $USER
   ```