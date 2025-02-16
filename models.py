from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    """Player model representing a golf player."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    handicap = db.Column(db.Float, nullable=False, default=0)
    scores = db.relationship('Score', backref='player', lazy=True)

    def __repr__(self):
        return f'<Player {self.name}>'

class Score(db.Model):
    """Score model representing a golf score entry."""
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)

    def formatted_date(self):
        """Return date in dd.mm.yy format."""
        return self.date.strftime('%d.%m.%y')
