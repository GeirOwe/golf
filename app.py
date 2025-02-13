# this app is deployed to Render
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

import os
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import inspect
from models import db, Player, Score

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.getenv('INSTANCE_DIR', os.path.join(BASE_DIR, "instance"))
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Ensure directory permissions
if os.path.exists(INSTANCE_DIR):
    os.chmod(INSTANCE_DIR, 0o777)

DB_PATH = os.getenv('DATABASE_URL', os.path.join(INSTANCE_DIR, "golf.db"))


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Use SQLite for local development, but allow override for production
    if DB_PATH.startswith('sqlite:///'):
        app.config["SQLALCHEMY_DATABASE_URI"] = DB_PATH
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app

app = create_app()


def database_exists():
    """Check if database tables exist."""
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            return inspector.has_table("player") and inspector.has_table("score")
    except Exception as e:
        print(f"Database check failed: {e}")
        return False

# Create database tables if they don't exist
with app.app_context():
    if not database_exists():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Failed to create database: {e}")


@app.route("/")
def home():
    """Render the home page with menu options."""
    return render_template("home.html")


@app.route("/register", methods=["GET"])
def register_player():
    """Render the player registration form."""
    return render_template("register_player.html")


@app.route("/players", methods=["GET"])
def list_players():
    """List all registered players."""
    players = Player.query.all()
    return render_template("list_players.html", players=players)


@app.route("/player/<int:player_id>/update_handicap", methods=["POST"])
def update_handicap(player_id):
    """Update a player's handicap."""
    player = Player.query.get_or_404(player_id)
    new_handicap = request.form.get("handicap")
    if new_handicap is not None:
        player.handicap = float(new_handicap)
        db.session.commit()
    return redirect(url_for("list_players"))


@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player and all their scores."""
    player = Player.query.get_or_404(player_id)
    Score.query.filter_by(player_id=player.id).delete()
    db.session.delete(player)
    db.session.commit()
    return redirect(url_for("list_players"))


@app.route("/add_player", methods=["POST"])
def add_player():
    """Add a new player to the database."""
    player_name = request.form.get("player_name")
    handicap = request.form.get("handicap", 0)
    if player_name:
        player = Player(name=player_name, handicap=float(handicap))
        db.session.add(player)
        db.session.commit()
    return redirect(url_for("home"))


@app.route("/scores")
def list_scores():
    """List all scores, ordered by date ascending."""
    scores = Score.query.order_by(Score.date.asc()).all()
    return render_template("list_scores.html", scores=scores)


@app.route("/score/<int:score_id>/delete", methods=["POST"])
def delete_score(score_id):
    """Delete a specific score."""
    score = Score.query.get_or_404(score_id)
    db.session.delete(score)
    db.session.commit()
    return redirect(url_for("list_scores"))


@app.route("/select_player_for_score")
def select_player_for_score():
    """Display player selection screen for score entry."""
    players = Player.query.all()
    return render_template("select_player_for_score.html", players=players)


@app.route("/player/<int:player_id>/add_score", methods=["GET", "POST"])
def add_score(player_id):
    """Add a score for the specified player."""
    player = Player.query.get_or_404(player_id)

    if request.method == "POST":
        score_value = request.form.get("score")
        if score_value:
            score = Score(value=int(score_value), player_id=player.id)
            db.session.add(score)
            db.session.commit()
            return redirect(url_for("add_score", player_id=player.id))

    return render_template("add_score.html", player=player)


# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")


if __name__ == "__main__":
    if not os.path.exists("instance/golf.db"):
        init_db()
    app.run(host="0.0.0.0", port=10000)
