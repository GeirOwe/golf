# this app is deployed to Render.
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

import os
from flask import Flask, render_template, request, redirect, url_for
from models import Player

app = Flask(__name__)

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
        Player(name=player_name, handicap=float(handicap))
    return redirect(url_for("home"))

@app.route("/players", methods=["GET"])
def list_players():
    """Display list of all players."""
    players = Player.get_all()
    return render_template("list_players.html", players=players)

@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player."""
    player = Player.get_by_id(player_id)
    if player:
        player.delete()
    return redirect(url_for("list_players"))

if __name__ == "__main__":
    app.run(debug=True)
