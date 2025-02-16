from flask_sqlalchemy import SQLAlchemy
from typing import List, Optional
from datetime import datetime
from models import HandicapError

db = SQLAlchemy()

class Player(db.Model):
    """Player model for PostgreSQL database."""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    handicap = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    MAX_HANDICAP = 36.0

    def __init__(self, name: str, handicap: float = 0):
        if handicap > self.MAX_HANDICAP:
            raise HandicapError(f"Handicap cannot be greater than {self.MAX_HANDICAP}")
        self.name = name
        self.handicap = handicap

    @classmethod
    def get_all(cls) -> List['Player']:
        """Return all players sorted by name."""
        return cls.query.order_by(cls.name).all()

    @classmethod
    def get_by_id(cls, player_id: int) -> Optional['Player']:
        """Find player by ID."""
        return cls.query.get(player_id)

    def delete(self):
        """Delete player from database."""
        db.session.delete(self)
        db.session.commit()

class Round(db.Model):
    """Round model for PostgreSQL database."""
    __tablename__ = 'rounds'
    
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    play_date = db.Column(db.DateTime, nullable=False)
    tee_time = db.Column(db.String(5), nullable=False)
    pick_up = db.Column(db.String(12))  # New field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_all(cls):
        """Return all rounds sorted by date ascending."""
        return cls.query.order_by(cls.play_date.asc()).all()

    @classmethod
    def get_by_id(cls, round_id):
        """Find round by ID."""
        return cls.query.get(round_id)

    def delete(self):
        """Delete round from database."""
        db.session.delete(self)
        db.session.commit()
    
    def get_player_score(self, player_id):
        """Get score for a specific player."""
        score = RoundScore.query.filter_by(
            round_id=self.id, 
            player_id=player_id
        ).first()
        return score.score if score else None

class RoundScore(db.Model):
    """Model for storing player scores for each round."""
    __tablename__ = 'round_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('rounds.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    round = db.relationship('Round', backref=db.backref('scores', lazy=True))
    player = db.relationship('Player', backref=db.backref('scores', lazy=True))
