# Golf Score Tracking App

A Flask web application for managing golf players, rounds, scores, and tournament info.  
Now with AI-powered golf advice and easy deployment on [Render](https://render.com).

---

## Features

- Player registration and management (max handicap: 54.0)
- Round creation with course, date, tee time, and pickup
- Score entry and Order of Merit table (excludes zeros from average)
- Flight assignments and daily dress code info
- Local rules page
- Norwegian date formatting
- **AI-powered golf advice** (via OpenAI or XAI API)
- Mobile-friendly design

---

## Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/yourusername/golf.git
cd golf
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://localhost/golf_dev
FLASK_ENV=development
OPENAI_API_KEY=your_openai_api_key_here
# or for XAI: XAI_API_KEY=your_xai_api_key_here
```

### 3. Run Locally

```bash
flask run
```

---

## Deployment on Render

1. Push your code to GitHub.
2. Create a new **Web Service** on [Render](https://render.com/).
3. Set your environment variables (`DATABASE_URL`, `OPENAI_API_KEY` or `XAI_API_KEY`) in the Render dashboard under the **Environment** tab.
4. Render will auto-install dependencies from `requirements.txt` and run your app.

---

## AI Integration

- `/ai-story` route generates a one/two-sentence golf tip using OpenAI or XAI.
- Requires a valid API key set as an environment variable.
- Error messages are shown on the page if the API call fails.

---

## Code Style

- Follows PEP 8 guidelines.
- Use flake8 for linting:

```bash
flake8 .
```

---

## Project Structure

```plaintext
golf/
├── app.py             # Flask application & routes
├── database.py        # Database models
├── models.py          # Custom exceptions
├── requirements.txt   # Project dependencies
├── .env               # Environment variables (not committed)
└── templates/         # HTML templates
    ├── base.html
    ├── home.html
    ├── list_players.html
    ├── list_rounds.html
    ├── list_scores.html
    ├── flight_setup.html
    ├── dress_code.html
    ├── local_rules.html
    ├── unicorn_story.html
    └── manage_scores.html
```

---

## License

MIT License

---

## Credits

- Built by Gary Owen & Diip Sikh
