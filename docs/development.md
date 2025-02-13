# Development Guide

## Setup
1. Clone repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Local Development
- Run development server:
  ```bash
  python app.py
  ```
- Access at: http://localhost:10000

## File Structure
```
golf/
├── app.py           # Main application
├── models.py        # Data models
├── data_store.py    # JSON storage handling
├── templates/       # HTML templates
├── data/           # JSON data files
└── docs/           # Documentation
```

## Data Storage
- Players stored in: `data/players.json`
- Scores stored in: `data/scores.json`
- Files automatically created if missing