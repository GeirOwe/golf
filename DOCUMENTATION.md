# Golf Tournament Management Application

## Overview
A Flask web application for managing golf tournament players, rounds, and scores.
Deployed on Render.com: https://golf-app-w497.onrender.com

## Setup

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/golf.git
cd golf
```

2. **Set Up Python Environment**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. **Environment Configuration**
Create a `.env` file:
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/golf_db
FLASK_ENV=development
```

## Project Structure
```plaintext
golf/
├── app.py             # Flask application & routes
├── database.py        # Database models
├── models.py          # Custom exceptions
├── requirements.txt   # Project dependencies
└── templates/         # HTML templates
    ├── base.html           # Base template with styling
    ├── home.html          # Home page
    ├── list_players.html  # Player listing
    ├── list_rounds.html   # Rounds listing
    ├── list_scores.html   # Score overview
    ├── flight_setup.html  # Flight assignments
    ├── dress_code.html    # Daily dress codes
    └── manage_scores.html # Score entry form
```

## Features

### Player Management
- Register players with handicap
- View player list
- Update player information
- Maximum handicap: 54.0

### Round Management
- Create new rounds with:
  - Course name
  - Play date
  - Tee time
  - Pickup location
- View all rounds
- Update round details

### Score Tracking
- Enter scores per player per round
- View total scores and averages
- Automatic calculation excluding zeros
- Order of Merit table

### Tournament Information
- Flight assignments per day
- Daily dress code requirements
- Norwegian date formatting

## Database Schema

### Players Table
```sql
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    handicap FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Rounds Table
```sql
CREATE TABLE rounds (
    id SERIAL PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    play_date TIMESTAMP NOT NULL,
    tee_time VARCHAR(5) NOT NULL,
    pick_up VARCHAR(12),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Round Scores Table
```sql
CREATE TABLE round_scores (
    id SERIAL PRIMARY KEY,
    round_id INTEGER REFERENCES rounds(id),
    player_id INTEGER REFERENCES players(id),
    score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Deployment
The application is deployed on Render.com using:
- Python 3.9+
- PostgreSQL database
- Gunicorn web server