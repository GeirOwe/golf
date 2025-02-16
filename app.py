# this app is deployed to Render
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

import os
from flask import Flask, render_template, request, redirect, url_for
from models import db, Player, Score

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'golf.db')

# Ensure instance directory exists
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

@app.route("/")
def home():
    """Render the home page."""
    return render_template("home.html")

@app.route("/register", methods=["GET"])
def register_player():
    """Display the player registration form."""
    return render_template("register_player.html")

@app.route("/add_player", methods=["POST"])
def add_player():
    """Handle new player registration."""
    player_name = request.form.get("player_name")
    handicap = request.form.get("handicap", 0)
    if player_name:
        player = Player(name=player_name, handicap=float(handicap))
        db.session.add(player)
        db.session.commit()
    return redirect(url_for("home"))

@app.route("/players", methods=["GET"])
def list_players():
    """Display list of all players."""
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
    """Delete a player and their associated scores."""
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)  # This will cascade delete scores
    db.session.commit()
    return redirect(url_for("list_players"))

@app.route("/scores")
def list_scores():
    """Display all scores, sorted by date."""
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
    """Display player selection for score entry."""
    players = Player.query.all()
    return render_template("select_player_for_score.html", players=players)

@app.route("/player/<int:player_id>/add_score", methods=["GET", "POST"])
def add_score(player_id):
    """Add or view scores for a specific player."""
    player = Player.query.get_or_404(player_id)

    if request.method == "POST":
        score_value = request.form.get("score")
        if score_value:
            score = Score(value=int(score_value), player_id=player.id)
            db.session.add(score)
            db.session.commit()
            return redirect(url_for("add_score", player_id=player.id))

    return render_template("add_score.html", player=player)

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True)
