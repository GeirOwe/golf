from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Player(db.Model):
    """Player model representing a golf player in the system.

    Attributes:
        id (int): Primary key for the player
        name (str): Player's name, must be unique
        handicap (float): Player's golf handicap, defaults to 0
        scores (relationship): One-to-many relationship with Score model
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    handicap = db.Column(db.Float, nullable=False, default=0)
    scores = db.relationship("Score", backref="player", lazy=True)

    def __repr__(self):
        """String representation of the Player object."""
        return f"<Player {self.name}>"


class Score(db.Model):
    """Score model representing a golf score entry.
    Attributes:
        id (int): Primary key for the score
        value (int): The actual score value
        date (datetime): When the score was recorded, auto-set to UTC
        player_id (int): Foreign key linking to the Player model
    """
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)

    def local_date(self):
        """Convert UTC date to local timezone.
        
        Returns:
            datetime: Score date in local timezone
        """
        return self.date.replace(tzinfo=timezone.utc).astimezone()
