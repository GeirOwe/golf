# this app is deployed to Render
# url: https://golf-app-w497.onrender.com
# dashboard on Render: https://dashboard.render.com/web/srv-cul4m20gph6c738frqj0
# OBS: Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.

from flask import Flask, render_template, request, redirect, url_for
from models import Player

app = Flask(__name__)

# Store players in memory (you might want to use a database later)
players = []

@app.route("/", methods=['GET'])
def home():
    return render_template('home.html', players=players)

@app.route("/add_player", methods=['POST'])
def add_player():
    player_name = request.form.get('player_name')
    handicap = request.form.get('handicap', 0)
    if player_name:
        player = Player(player_name, float(handicap))
        players.append(player)
    return redirect(url_for('home'))

if __name__ == '__main__':
    # This is used when running locally
    app.run(host='0.0.0.0', port=10000)