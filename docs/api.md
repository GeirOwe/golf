# API Documentation

## Routes

### Players
- `GET /` - Home page
- `GET /register` - Player registration form
- `POST /add_player` - Create new player
- `GET /players` - List all players
- `POST /player/<id>/update_handicap` - Update player handicap
- `POST /player/<id>/delete` - Delete player and scores

### Scores
- `GET /scores` - List all scores
- `GET /select_player_for_score` - Select player for new score
- `GET/POST /player/<id>/add_score` - Add/view player scores
- `POST /score/<id>/delete` - Delete specific score

## Data Models

### Player
```python
{
    "id": int,
    "name": str,
    "handicap": float
}
```

### Score
```python
{
    "id": int,
    "value": int,
    "player_id": int,
    "date": str  # ISO format
}
```