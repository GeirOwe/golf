"""
Golf Application
---------------
A Flask web application for managing golf players and rounds.
Deployed on Render.com: https://golf-app-w497.onrender.com
"""

import os
from datetime import datetime
import locale
from flask import Flask, render_template, request, redirect, url_for
from database import db, Player, Round, RoundScore  # Add RoundScore to imports
from models import HandicapError
from dotenv import load_dotenv
from openai import OpenAI

# Set Norwegian locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, 'nb_NO.UTF-8')
except locale.Error:
    # Fallback if Norwegian locale is not available
    locale.setlocale(locale.LC_TIME, '')

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Environment Configuration
    if os.environ.get('FLASK_ENV') != 'production':
        load_dotenv()
    
    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    return app

# Initialize application
app = create_app()

# Ensure database tables exist
with app.app_context():
    db.create_all()

# Basic Routes
@app.route("/")
def home():
    """Render the home page."""
    return render_template("home.html")

# Player Management Routes
@app.route("/register", methods=["GET"])
def register_player():
    """Display the player registration form."""
    return render_template("register_player.html")

@app.route("/add_player", methods=["POST"])
def add_player():
    """Handle new player registration with handicap validation."""
    player_name = request.form.get("player_name")
    handicap = float(request.form.get("handicap", 0))
    
    try:
        if player_name:
            player = Player(name=player_name, handicap=handicap)
            db.session.add(player)
            db.session.commit()
            return redirect(url_for("home"))
    except HandicapError as e:
        return render_template("register_player.html", error=str(e))
    
    return redirect(url_for("home"))

@app.route("/players", methods=["GET"])
def list_players():
    """Display list of all players sorted by name."""
    players = Player.get_all()
    return render_template("list_players.html", players=players)

@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player."""
    player = Player.get_by_id(player_id)
    if player:
        player.delete()
    return redirect(url_for("list_players"))

@app.route("/player/<int:player_id>/update", methods=["GET", "POST"])
def update_player(player_id):
    """Update a player's information with handicap validation."""
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

# Round Management Routes
@app.route("/rounds")
def list_rounds():
    """Display list of all rounds sorted by date."""
    rounds = Round.get_all()
    return render_template("list_rounds.html", rounds=rounds)

@app.route("/round/new", methods=["GET", "POST"])
def add_round():
    """Handle new round registration."""
    if request.method == "POST":
        course_name = request.form.get("course_name")
        play_date = datetime.strptime(request.form.get("play_date"), "%Y-%m-%d")
        tee_time = request.form.get("tee_time")
        pick_up = request.form.get("pick_up")
        
        if course_name and play_date and tee_time:
            round = Round(
                course_name=course_name,
                play_date=play_date,
                tee_time=tee_time,
                pick_up=pick_up
            )
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

@app.route("/round/<int:round_id>/update", methods=["GET", "POST"])
def update_round(round_id):
    """Update a round's information."""
    round = Round.get_by_id(round_id)
    if not round:
        return redirect(url_for("list_rounds"))
    
    if request.method == "POST":
        round.course_name = request.form.get("course_name", round.course_name)
        play_date = request.form.get("play_date")
        if play_date:
            round.play_date = datetime.strptime(play_date, "%Y-%m-%d")
        round.tee_time = request.form.get("tee_time", round.tee_time)
        db.session.commit()
        return redirect(url_for("list_rounds"))
        
    return render_template("update_round.html", round=round)

@app.route("/round/<int:round_id>/scores", methods=["GET", "POST"])
def manage_scores(round_id):
    """Manage scores for a round."""
    round = Round.get_by_id(round_id)
    if not round:
        return redirect(url_for("list_rounds"))
    
    players = Player.get_all()
    
    if request.method == "POST":
        # Update scores
        for player in players:
            score = request.form.get(f"score_{player.id}")
            if score:
                # Update or create score
                round_score = RoundScore.query.filter_by(
                    round_id=round.id,
                    player_id=player.id
                ).first()
                
                if round_score:
                    round_score.score = int(score)
                else:
                    round_score = RoundScore(
                        round_id=round.id,
                        player_id=player.id,
                        score=int(score)
                    )
                    db.session.add(round_score)
        
        db.session.commit()
        return redirect(url_for("list_rounds"))
    
    return render_template("manage_scores.html", round=round, players=players)

@app.route("/scores")
def list_scores():
    """Display player scores sorted by total score."""
    players = Player.get_all()
    
    # Get scores for each player
    player_scores = []
    for player in players:
        scores = RoundScore.query.filter_by(player_id=player.id).all()
        if scores:
            # Filter out zeros and empty scores
            valid_scores = [score.score for score in scores if score.score]
            if valid_scores:  # Only process if there are valid scores
                total_score = sum(valid_scores)
                avg_score = round(total_score / len(valid_scores), 1)
                player_scores.append({
                    'name': player.name,
                    'total': total_score,
                    'avg': avg_score,
                    'scores': valid_scores
                })
    
    # Sort by total score descending
    player_scores.sort(key=lambda x: x['total'], reverse=True)
    
    return render_template("list_scores.html", player_scores=player_scores)

@app.route("/scores/reset", methods=["POST"])
def reset_scores():
    """Delete all registered scores."""
    try:
        RoundScore.query.delete()
        db.session.commit()
        return redirect(url_for("list_scores", message="Alle scorer er slettet"))
    except Exception as e:
        return redirect(url_for("list_scores", error=f"Kunne ikke slette scorer: {str(e)}"))

@app.route("/admin/db/reset", methods=["POST"])
def reset_database():
    """Reset and reinitialize the database."""
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
        return redirect(url_for("home", message="Database reset successfully"))
    except Exception as e:
        return redirect(url_for("home", error=f"Database reset failed: {str(e)}"))

@app.route("/flights")
def show_flights():
    """Display the flight setup for each day."""
    return render_template("flight_setup.html")

@app.route("/dress-code")
def show_dress_code():
    """Display the static dress code information."""
    return render_template("dress_code.html")

@app.route("/local-rules")
def show_local_rules():
    """Display the local rules for the tournament."""
    return render_template("local_rules.html")

@app.route("/ai-story")
def unicorn_story():
    """Generate and display an AI story."""
    story = None
    error = None
    try:
        client = OpenAI()
        response = client.responses.create(
            model="gpt-4.1-nano",
            input="Write a one-sentence joke about golf."
        )
        story = response.output_text
    except Exception as e:
        error = f"Feil ved henting av AI-historie: {str(e)}"
    return render_template("unicorn_story.html", story=story, error=error)

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

# Run application
if __name__ == "__main__":
    app.run(debug=True)
