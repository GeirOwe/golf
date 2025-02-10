# Golf Application Technical Documentation

## Architecture Overview
The application follows a Model-View-Controller (MVC) pattern using Flask:
- Models: SQLAlchemy database models
- Views: Jinja2 HTML templates
- Controllers: Flask routes in app.py

## Database Schema

### Player Model
```python
class Player(db.Model):
    id: Integer (Primary Key)
    name: String(80) (Unique, Required)
    handicap: Float (Required, Default=0)
    scores: Relationship to Score model
```

### Score Model
```python
class Score(db.Model):
    id: Integer (Primary Key)
    value: Integer (Required)
    date: DateTime (Required, UTC)
    player_id: Integer (Foreign Key to Player)
```

## API Routes

### Player Management
- `GET /`: Home page
- `GET /register`: Player registration form
- `POST /add_player`: Create new player
- `GET /players`: List all players
- `POST /player/<id>/update_handicap`: Update player handicap
- `POST /player/<id>/delete`: Delete player and scores

### Score Management
- `GET /select_player_for_score`: Select player for scoring
- `GET /player/<id>/add_score`: Score input form
- `POST /player/<id>/add_score`: Save new score
- `GET /scores`: View all scores
- `POST /score/<id>/delete`: Delete score

## Template Structure
```
templates/
├── base.html          # Base template with common styling
├── home.html          # Main menu
├── register_player.html    # Player registration form
├── list_players.html      # Player list and management
├── add_score.html        # Score input form
├── list_scores.html      # Score history view
└── select_player_for_score.html  # Player selection for scoring
```

## Dependencies
- Flask: Web framework
- SQLAlchemy: Database ORM
- Gunicorn: WSGI HTTP Server
- Python-dotenv: Environment management

## Deployment
The application is deployed on Render:
- URL: https://golf-app-w497.onrender.com
- Environment: Python
- Database: SQLite

## Development Setup
See README.md for detailed setup instructions including:
- Virtual environment setup
- Dependencies installation
- Database initialization
- Local development server

## Code Style
- Follows PEP 8 guidelines
- Uses flake8 for linting
- Maximum line length: 88 characters