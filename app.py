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

@app.route("/", methods=['GET'])
def home():
    players = Player.query.all()
    return render_template('home.html', players=players)

@app.route("/add_player", methods=['POST'])
def add_player():
    player_name = request.form.get('player_name')
    handicap = request.form.get('handicap', 0)
    if player_name:
        player = Player(name=player_name, handicap=float(handicap))
        db.session.add(player)
        db.session.commit()
    return redirect(url_for('home'))

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

if __name__ == '__main__':
    if not os.path.exists('instance/golf.db'):
        init_db()
    app.run(host='0.0.0.0', port=10000)