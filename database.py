import secrets

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from datetime import datetime
from models import HandicapError

db = SQLAlchemy()


def _new_group_token():
    return secrets.token_urlsafe()


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=_new_group_token)
    players = db.relationship(
        "Player",
        backref="group",
        order_by=lambda: Player.name,
    )


class Player(db.Model):
    __tablename__ = "players"
    MAX_HANDICAP = 54.0

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    handicap = db.Column(db.Float, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)

    def __init__(self, name, handicap, group_id):
        self.group_id = group_id
        self._assign(name, handicap)

    def change(self, name, handicap):
        self._assign(name, handicap)

    def _assign(self, name, handicap):
        if handicap > self.MAX_HANDICAP:
            raise HandicapError(
                f"Handicap kan ikke være høyere enn {self.MAX_HANDICAP:.1f}."
            )
        self.name = name
        self.handicap = handicap

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.name).all()

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
        """Delete round and its scores from database."""
        RoundScore.query.filter_by(round_id=self.id).delete()
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


class GolfCourse(db.Model):
    """Golf course with facility info and tee boxes."""
    __tablename__ = 'golf_courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    facility = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tees = db.relationship(
        'CourseTee',
        backref='course',
        lazy=True,
        cascade='all, delete-orphan',
        order_by=lambda: desc(CourseTee.course_rating),
    )

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.name.asc()).all()

    @classmethod
    def get_by_id(cls, course_id):
        return cls.query.get(course_id)


class CourseTee(db.Model):
    """Tee box data for slope, CR and par (used for mottatte slag)."""
    __tablename__ = 'course_tees'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('golf_courses.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False, default='Herre')
    par = db.Column(db.Integer, nullable=False)
    course_rating = db.Column(db.Float, nullable=False)
    slope_rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
