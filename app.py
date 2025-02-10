# this app is deployed to Render
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

from flask import Flask, render_template, request, redirect, url_for
from models import db, Player, Score
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///golf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/register", methods=['GET'])
def register_player():
    return render_template('register_player.html')

@app.route("/players", methods=['GET'])
def list_players():
    players = Player.query.all()
    return render_template('list_players.html', players=players)

@app.route("/player/<int:player_id>/update_handicap", methods=['POST'])
def update_handicap(player_id):
    player = Player.query.get_or_404(player_id)
    new_handicap = request.form.get('handicap')
    if new_handicap is not None:
        player.handicap = float(new_handicap)
        db.session.commit()
    return redirect(url_for('list_players'))

@app.route("/player/<int:player_id>/delete", methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    # Delete all scores associated with the player
    Score.query.filter_by(player_id=player.id).delete()
    # Delete the player
    db.session.delete(player)
    db.session.commit()
    return redirect(url_for('list_players'))

@app.route("/add_player", methods=['POST'])
def add_player():
    player_name = request.form.get('player_name')
    handicap = request.form.get('handicap', 0)
    if player_name:
        player = Player(name=player_name, handicap=float(handicap))
        db.session.add(player)
        db.session.commit()
    return redirect(url_for('home'))

@app.route("/player/<int:player_id>/add_score", methods=['GET', 'POST'])
def add_score(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        score_value = request.form.get('score')
        if score_value:
            score = Score(value=int(score_value), player_id=player.id)
            db.session.add(score)
            db.session.commit()
            return redirect(url_for('add_score', player_id=player.id))
    
    return render_template('add_score.html', player=player)

@app.route("/scores")
def list_scores():
    scores = Score.query.order_by(Score.date.desc()).all()
    return render_template('list_scores.html', scores=scores)

@app.route("/score/<int:score_id>/delete", methods=['POST'])
def delete_score(score_id):
    score = Score.query.get_or_404(score_id)
    db.session.delete(score)
    db.session.commit()
    return redirect(url_for('list_scores'))

@app.route("/select_player_for_score")
def select_player_for_score():
    players = Player.query.all()
    return render_template('select_player_for_score.html', players=players)

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

if __name__ == '__main__':
    if not os.path.exists('instance/golf.db'):
        init_db()
    app.run(host='0.0.0.0', port=10000)