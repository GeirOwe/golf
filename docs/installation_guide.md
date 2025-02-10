# Installation and Deployment Guide

## Local Flask Setup

### 1. Initial Project Setup
```bash
# Create project directory
mkdir golf
cd golf

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install initial dependencies
pip install flask
pip install flask-sqlalchemy
pip install python-dotenv
```

### 2. Install Development Tools
```bash
# Install code quality tools
pip install flake8
pip install black

# Install testing tools
pip install pytest
```

### 3. Create Requirements File
```bash
# Generate requirements.txt
pip freeze > requirements.txt
```

### 4. Project Structure Setup
```bash
# Create necessary directories
mkdir templates
mkdir instance
mkdir docs

# Create initial files
touch app.py
touch models.py
touch .env
touch .gitignore
```

## Render Deployment

### 1. Prerequisites Setup
```bash
# Install Gunicorn
pip install gunicorn

# Update requirements.txt
pip freeze > requirements.txt
```

### 2. Configuration Files

```python
# filepath: gunicorn_config.py
bind = "0.0.0.0:10000"
workers = 2
timeout = 120
```

```text
# filepath: Procfile
web: gunicorn app:app
```

### 3. Render Dashboard Steps
1. Create New Web Service
   - Connect to GitHub repository
   - Select Python environment
   - Choose branch (main)

2. Configure Build Settings
   ```text
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app
   ```

3. Set Environment Variables
   ```text
   PYTHON_VERSION=3.9.0
   FLASK_APP=app.py
   FLASK_ENV=production
   ```

### 4. Version Control
```bash
# Initialize Git repository
git init

# Add files
git add .

# Initial commit
git commit -m "Initial commit"

# Add remote repository
git remote add origin <your-github-repo-url>

# Push to GitHub
git push -u origin main
```

## Verify Installation

### Local Development
```bash
# Run Flask application
flask run

# Access application
open http://localhost:5000
```

### Render Deployment
1. Wait for build completion
2. Access provided Render URL
3. Verify all features:
   - Player registration
   - Score entry
   - Database operations

## Troubleshooting

### Local Issues
```bash
# Check Python version
python3 --version

# Verify virtual environment
which python

# Check installed packages
pip list

# Verify database
flask shell
>>> from app import db
>>> db.create_all()
```

### Render Issues
1. Check build logs in Render dashboard
2. Verify environment variables
3. Check application logs
4. Confirm database initialization

## Maintenance

### Update Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Update packages
pip install --upgrade -r requirements.txt

# Update requirements.txt
pip freeze > requirements.txt
```

### Deploy Updates
```bash
# Commit changes
git add .
git commit -m "Update application"

# Push to trigger deployment
git push origin main
```