from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    """Player model for PostgreSQL database."""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    handicap = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_all(cls):
        """Return all players."""
        return cls.query.all()

    @classmethod
    def get_by_id(cls, player_id):
        """Find player by ID."""
        return cls.query.get(player_id)

    def delete(self):
        """Delete player from database."""
        db.session.delete(self)
        db.session.commit()