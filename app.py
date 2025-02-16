# this app is deployed to Render.
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

import os
from flask import Flask, render_template, request, redirect, url_for
from database import db, Player, Round
from models import HandicapError
from dotenv import load_dotenv
from datetime import datetime
import locale
try:
    locale.setlocale(locale.LC_TIME, 'nb_NO.UTF-8')
except locale.Error:
    # Fallback for systems without Norwegian locale
    locale.setlocale(locale.LC_TIME, '')

# Initialize Flask application
def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load environment variables
    if os.environ.get('FLASK_ENV') != 'production':
        load_dotenv()
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app

app = create_app()

# Ensure database tables exist
with app.app_context():
    db.create_all()

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
    handicap = float(request.form.get("handicap", 0))
    
    try:
        if player_name:
            Player(name=player_name, handicap=handicap)
            return redirect(url_for("home"))
    except HandicapError as e:
        return render_template("register_player.html", error=str(e))
    
    return redirect(url_for("home"))

@app.route("/players", methods=["GET"])
def list_players():
    """Display list of all players."""
    players = Player.get_all()  # Using class method
    return render_template("list_players.html", players=players)

@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player."""
    player = Player.get_by_id(player_id)  # Using class method
    if player:
        player.delete()
    return redirect(url_for("list_players"))

@app.route("/player/<int:player_id>/update", methods=["GET", "POST"])
def update_player(player_id):
    """Update a player's information."""
    player = Player.get_by_id(player_id)
    if not player:
        return redirect(url_for("list_players"))
    
    if request.method == "POST":
        new_handicap = float(request.form.get("handicap", player.handicap))
        if new_handicap > Player.MAX_HANDICAP:
            return render_template("update_player.html", 
                                player=player, 
                                error=f"Handicap cannot be greater than {Player.MAX_HANDICAP}")
        
        player.name = request.form.get("player_name", player.name)
        player.handicap = new_handicap
        db.session.commit()
        return redirect(url_for("list_players"))
        
    return render_template("update_player.html", player=player)

@app.route("/rounds")
def list_rounds():
    """Display list of all rounds."""
    rounds = Round.get_all()
    return render_template("list_rounds.html", rounds=rounds)

@app.route("/round/new", methods=["GET", "POST"])
def add_round():
    """Handle new round registration."""
    if request.method == "POST":
        course_name = request.form.get("course_name")
        play_date = datetime.strptime(request.form.get("play_date"), "%Y-%m-%d")
        tee_time = request.form.get("tee_time")
        
        if course_name and play_date and tee_time:
            round = Round(course_name=course_name, play_date=play_date, tee_time=tee_time)
            db.session.add(round)
            db.session.commit()
            return redirect(url_for("list_rounds"))
    
    return render_template("add_round.html")

@app.route("/round/<int:round_id>/delete", methods=["POST"])
def delete_round(round_id):
    """Delete a round."""
    round = Round.get_by_id(round_id)
    if round:
        round.delete()
    return redirect(url_for("list_rounds"))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)
