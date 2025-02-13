import json
import os
from datetime import datetime

# Use environment variable for data directory or default to 'data'
DATA_DIR = os.getenv('DATA_DIR', 'data')
PLAYERS_FILE = os.path.join(DATA_DIR, 'players.json')
SCORES_FILE = os.path.join(DATA_DIR, 'scores.json')

def ensure_data_files():
    """Ensure data directory and files exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Create empty JSON files if they don't exist
    if not os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'w') as f:
            json.dump([], f)

def load_players():
    """Load players from JSON file."""
    ensure_data_files()
    with open(PLAYERS_FILE, 'r') as f:
        return json.load(f)

def save_players(players):
    """Save players to JSON file."""
    ensure_data_files()
    with open(PLAYERS_FILE, 'w') as f:
        json.dump(players, f, indent=2)

def load_scores():
    """Load scores from JSON file."""
    ensure_data_files()
    with open(SCORES_FILE, 'r') as f:
        return json.load(f)

def save_scores(scores):
    """Save scores to JSON file."""
    ensure_data_files()
    with open(SCORES_FILE, 'w') as f:
        json.dump(scores, f, indent=2)