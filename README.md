# Golf Score Tracking App

## Features
- Player registration and management

## Quick Start

### 1. Create Virtual Environment
```bash
# Create a new virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install Requirements
```bash
# Install all dependencies
pip install -r requirements.txt
```

### 4. Run Flask Application
```bash
# Set development environment
export FLASK_ENV=development
export FLASK_APP=app.py

# Run the application
flask run
```

## Development

### Code Style
This project follows PEP 8 style guidelines. We use flake8 for code linting.

### Running Code Style Checks
```bash
flake8 app.py models.py
```

## Project Structure
- `app.py`: Main Flask application
- `models.py`: Database models
- `templates/`: HTML templates
- `.flake8`: Flake8 configuration
