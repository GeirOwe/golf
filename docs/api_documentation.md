# API Documentation

## Player Endpoints

### GET /players
Lists all registered players.

**Response:**
- HTML page with player list
- Shows name, handicap, and actions for each player

### POST /add_player
Creates a new player.

**Parameters:**
- player_name (required): String
- handicap (optional): Float, defaults to 0

## Score Endpoints

### GET /scores
Lists all recorded scores.

**Response:**
- HTML page with score history
- Shows player name, score value, and date

### POST /player/{id}/add_score
Adds a new score for a player.

**Parameters:**
- score (required): Integer
- player_id (required): Integer