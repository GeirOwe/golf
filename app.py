# this app is deployed to Render.
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

from flask import Flask, render_template, request, redirect, url_for
import os
from models import db, Player, Score
from sqlalchemy import inspect

# Create instance directory with absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'golf.db')

# Ensure instance directory exists with proper permissions
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.chmod(INSTANCE_DIR, 0o777)  # Full permissions for debugging

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

def database_exists():
    """Check if database tables exist."""
    with app.app_context():
        inspector = inspect(db.engine)
        return inspector.has_table("player") and inspector.has_table("score")

# Only create tables if they don't exist
if not database_exists():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")


@app.route("/")
def home():
    """Render the home page with menu options.

    Returns:
        Rendered home template
    """
    return render_template("home.html")


@app.route("/register", methods=["GET"])
def register_player():
    """Render the player registration form.

    Returns:
        Rendered registration template
    """
    return render_template("register_player.html")


@app.route("/players", methods=["GET"])
def list_players():
    """List all registered players.

    Returns:
        Rendered template with all players
    """
    players = Player.query.all()
    return render_template("list_players.html", players=players)


@app.route("/player/<int:player_id>/update_handicap", methods=["POST"])
def update_handicap(player_id):
    """Update a player's handicap.

    Args:
        player_id (int): ID of the player to update

    Returns:
        Redirect to player list
    """
    player = Player.query.get_or_404(player_id)
    new_handicap = request.form.get("handicap")
    if new_handicap is not None:
        player.handicap = float(new_handicap)
        db.session.commit()
    return redirect(url_for("list_players"))


@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player and all their scores.

    Args:
        player_id (int): ID of the player to delete

    Returns:
        Redirect to player list
    """
    player = Player.query.get_or_404(player_id)
    Score.query.filter_by(player_id=player.id).delete()
    db.session.delete(player)
    db.session.commit()
    return redirect(url_for("list_players"))


@app.route("/add_player", methods=["POST"])
def add_player():
    """Add a new player to the database.

    Returns:
        Redirect to home page
    """
    player_name = request.form.get("player_name")
    handicap = request.form.get("handicap", 0)
    if player_name:
        player = Player(name=player_name, handicap=float(handicap))
        db.session.add(player)
        db.session.commit()
    return redirect(url_for("home"))


@app.route("/player/<int:player_id>/add_score", methods=["GET", "POST"])
def add_score(player_id):
    """Add a score for the specified player.

    Args:
        player_id: Integer ID of the player

    Returns:
        Rendered template or redirect response
    """
    player = Player.query.get_or_404(player_id)

    if request.method == "POST":
        score_value = request.form.get("score")
        if score_value:
            score = Score(value=int(score_value), player_id=player.id)
            db.session.add(score)
            db.session.commit()
            return redirect(url_for("add_score", player_id=player.id))

    return render_template("add_score.html", player=player)


@app.route("/scores")
def list_scores():
    """List all scores, ordered by date descending.

    Returns:
        Rendered template with all scores
    """
    scores = Score.query.order_by(Score.date.desc()).all()
    return render_template("list_scores.html", scores=scores)


@app.route("/score/<int:score_id>/delete", methods=["POST"])
def delete_score(score_id):
    """Delete a specific score.

    Args:
        score_id (int): ID of the score to delete

    Returns:
        Redirect to scores list
    """
    score = Score.query.get_or_404(score_id)
    db.session.delete(score)
    db.session.commit()
    return redirect(url_for("list_scores"))


@app.route("/select_player_for_score")
def select_player_for_score():
    """Display player selection screen for score entry.

    Returns:
        Rendered template with list of players
    """
    players = Player.query.all()
    return render_template("select_player_for_score.html", players=players)


# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")


if __name__ == "__main__":
    if not os.path.exists("instance/golf.db"):
        init_db()
    app.run(host="0.0.0.0", port=10000)
