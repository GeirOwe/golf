# Golf Score Tracking App

## Features
- Player registration and management
- Score tracking for each player
- Handicap management
- Score history view

## Documentation
Detailed documentation can be found in the `docs` folder:
- [Installation Guide](docs/installation_guide.md) - Complete setup and deployment instructions
- [Technical Documentation](docs/technical_documentation.md)
- [API Documentation](docs/api_documentation.md)
- [Database Documentation](docs/database_documentation.md)

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
```

See [Installation Guide](docs/installation_guide.md) for complete setup and deployment instructions.

## Development

### Code Style
This project follows PEP 8 style guidelines. We use flake8 for code linting.

### Running Code Style Checks
```bash
flake8 app.py models.py
```

## Deployment
The application is deployed on Render. See [Installation Guide](docs/installation_guide.md) for deployment instructions.

## Project Structure
- `app.py`: Main Flask application
- `models.py`: Database models
- `templates/`: HTML templates
- `instance/`: Database files
- `docs/`: Project documentation
- `.flake8`: Flake8 configuration
