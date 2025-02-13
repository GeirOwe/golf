# this app is deployed to Render
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

import os
from flask import Flask, render_template, request, redirect, url_for
from models import Player, Score
from data_store import ensure_data_files

app = Flask(__name__)

# Ensure data directory and files exist on startup
ensure_data_files()

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
        player.save()
    return redirect(url_for("home"))

@app.route("/players", methods=["GET"])
def list_players():
    """Display list of all players."""
    players = Player.get_all()
    return render_template("list_players.html", players=players)

@app.route("/player/<int:player_id>/update_handicap", methods=["POST"])
def update_handicap(player_id):
    """Update a player's handicap."""
    player = Player.get_by_id(player_id)
    if player:
        new_handicap = request.form.get("handicap")
        if new_handicap is not None:
            player.handicap = float(new_handicap)
            player.save()
    return redirect(url_for("list_players"))

@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player and their associated scores."""
    player = Player.get_by_id(player_id)
    if player:
        # Delete associated scores first
        scores = Score.get_all()
        for score in scores:
            if score.player_id == player_id:
                score.delete()
        player.delete()
    return redirect(url_for("list_players"))

@app.route("/scores")
def list_scores():
    """Display all scores, sorted by date."""
    scores = sorted(Score.get_all(), key=lambda s: s.date)
    return render_template("list_scores.html", scores=scores)

@app.route("/score/<int:score_id>/delete", methods=["POST"])
def delete_score(score_id):
    """Delete a specific score."""
    score = Score.get_by_id(score_id)
    if score:
        score.delete()
    return redirect(url_for("list_scores"))

@app.route("/select_player_for_score")
def select_player_for_score():
    """Display player selection for score entry."""
    players = Player.get_all()
    return render_template("select_player_for_score.html", players=players)

@app.route("/player/<int:player_id>/add_score", methods=["GET", "POST"])
def add_score(player_id):
    """Add or view scores for a specific player."""
    player = Player.get_by_id(player_id)
    if not player:
        return redirect(url_for("home"))

    if request.method == "POST":
        score_value = request.form.get("score")
        if score_value:
            score = Score(value=int(score_value), player_id=player.id)
            score.save()
            return redirect(url_for("add_score", player_id=player.id))

    # Get and sort player's scores for display
    scores = [s for s in Score.get_all() if s.player_id == player.id]
    player.scores = sorted(scores, key=lambda s: s.date, reverse=True)
    return render_template("add_score.html", player=player)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
