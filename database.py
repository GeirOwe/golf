import math
import secrets

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, desc
from models import HandicapError

db = SQLAlchemy()

_WEEKDAYS_NO = (
    "Mandag",
    "Tirsdag",
    "Onsdag",
    "Torsdag",
    "Fredag",
    "Lørdag",
    "Søndag",
)

_WEEKDAYS_SHORT = ("man", "tir", "ons", "tor", "fre", "lør", "søn")


def _new_group_token():
    return secrets.token_urlsafe()


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=_new_group_token)
    players = db.relationship(
        "Player",
        backref="group",
        order_by=lambda: (Player.handicap, Player.name),
    )
    trips = db.relationship(
        "Trip",
        backref="group",
        cascade="all, delete-orphan",
        order_by=lambda: (Trip.created_at.desc(), Trip.id.desc()),
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
        if isinstance(handicap, bool) or not isinstance(handicap, (int, float)):
            raise HandicapError("Skriv et handicap fra 0.0 til 54.0.")
        if not math.isfinite(handicap) or handicap < 0:
            raise HandicapError("Skriv et handicap fra 0.0 til 54.0.")
        if handicap > self.MAX_HANDICAP:
            raise HandicapError(
                f"Handicap kan ikke være høyere enn {self.MAX_HANDICAP:.1f}."
            )
        self.name = name
        self.handicap = handicap

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.name).all()


class Trip(db.Model):
    __tablename__ = "trips"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    destination_name = db.Column(db.String(120), nullable=False)
    yr_location_id = db.Column(db.String(40))
    local_rules = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    memberships = db.relationship(
        "TripPlayer",
        backref="trip",
        cascade="all, delete-orphan",
    )

    def members(self):
        return sorted(
            self.memberships,
            key=lambda membership: membership.player.name.casefold(),
        )


class TripPlayer(db.Model):
    __tablename__ = "trip_players"
    __table_args__ = (
        UniqueConstraint("trip_id", "player_id", name="uq_trip_player"),
    )

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trips.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    handicap = db.Column(db.Float, nullable=False)
    finale_bonus = db.Column(db.Integer)
    player = db.relationship(
        "Player",
        backref=db.backref("memberships", cascade="all, delete-orphan"),
    )


class Round(db.Model):
    __tablename__ = "rounds"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trips.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("golf_courses.id"), nullable=False)
    tee_id = db.Column(db.Integer, db.ForeignKey("course_tees.id"), nullable=False)
    play_date = db.Column(db.Date, nullable=False)
    tee_time = db.Column(db.String(5), nullable=False)
    pick_up = db.Column(db.String(12))
    kind = db.Column(db.String(10), nullable=False, default="oom")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trip = db.relationship(
        "Trip",
        backref=db.backref(
            "rounds",
            cascade="all, delete-orphan",
            order_by=lambda: Round.play_date.asc(),
        ),
    )
    course = db.relationship("GolfCourse")
    tee = db.relationship("CourseTee")

    @property
    def display_date(self):
        return f"{_WEEKDAYS_NO[self.play_date.weekday()]} {self.play_date.strftime('%d.%m')}"

    @property
    def short_weekday(self):
        return _WEEKDAYS_SHORT[self.play_date.weekday()]

    @property
    def short_date(self):
        return self.play_date.strftime("%d.%m")


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
    player = db.relationship(
        'Player',
        backref=db.backref('scores', lazy=True, cascade='all, delete-orphan'),
    )


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
