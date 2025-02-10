# Golf Score Tracking App

## Features
- Player registration and management
- Score tracking for each player
- Handicap management
- Score history view

## Development Setup

### 1. Create Virtual Environment
```bash
# Create a new virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# To deactivate the virtual environment when you're done:
deactivate

```

### 2. Install Requirements
```bash
# Install all dependencies
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
# Create the database
python init_db.py
```

### 4. Run Flask Application
```bash
# Set development environment
export FLASK_ENV=development
export FLASK_APP=app.py

# Run the application
flask run
# or
python app.py
```

### 5. Access Application
Open http://localhost:5000 in your web browser

## Development Commands

### Start Debug Mode in VS Code
1. Press `F5` to start debugging
2. Select "Python: Flask" configuration
3. Access http://localhost:5000

### Code Style
This project follows PEP 8 style guidelines. We use flake8 for code linting.

#### Running Code Style Checks
```bash
flake8 app.py models.py
```

## Project Structure
- `app.py`: Main Flask application
- `models.py`: Database models
- `templates/`: HTML templates
- `instance/`: Database files
- `.flake8`: Flake8 configuration
- `venv/`: Virtual environment (not tracked in git)

## Common Issues

### Port Already in Use
```bash
# Kill process using port 5000
lsof -i :5000
kill -9 <PID>
```

### Database Reset
```bash
# Remove existing database
rm instance/golf.db

# Reinitialize database
python init_db.py
```

## Deployment to Render

### Prerequisites
- A Render account
- Your code pushed to GitHub
- Valid `requirements.txt`
- `gunicorn` in requirements

### Setup on Render
1. Create New Web Service
2. Connect your GitHub repository
3. Configure service:
   - Name: `golf-app`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

### Environment Variables
Set in Render dashboard:
```bash
PYTHON_VERSION=3.9.0
FLASK_APP=app.py
```

### Database
Render will create a new database in the `instance` folder during deployment.

### Logs
View application logs in Render dashboard for troubleshooting.
