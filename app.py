import hmac
import os
import re
from datetime import date, datetime

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, session, url_for
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import CourseTee, GolfCourse, Group, Player, Round, RoundScore, Trip, TripPlayer, db
from models import HandicapError, course_handicap
from scoring import oom_table


def ensure_course_tee_gender_column():
    """Add course_tees.gender for existing databases missing this column."""
    try:
        db.session.execute(text(
            "ALTER TABLE course_tees ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT 'Herre'"
        ))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


TEE_GENDERS = ("Herre", "Dame")
_YR_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,39}$")
_TEE_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _parse_tee_rows_from_form(form):
    """Parse tee rows from form lists. Returns list of dicts or error message."""
    tee_ids = form.getlist("tee_id")
    tee_names = form.getlist("tee_name")
    tee_genders = form.getlist("tee_gender")
    tee_pars = form.getlist("tee_par")
    tee_crs = form.getlist("tee_cr")
    tee_slopes = form.getlist("tee_slope")

    rows = []
    for tee_id, name, gender, par, cr, slope in zip(
        tee_ids, tee_names, tee_genders, tee_pars, tee_crs, tee_slopes
    ):
        name = (name or "").strip()
        if not name:
            continue
        gender = (gender or "").strip()
        if gender not in TEE_GENDERS:
            return None, f"Ugyldig kjønn for tee «{name}». Velg Herre eller Dame."
        try:
            rows.append({
                "tee_id": int(tee_id) if (tee_id or "").strip().isdigit() else None,
                "name": name,
                "gender": gender,
                "par": int(par),
                "course_rating": float(cr),
                "slope_rating": int(slope),
            })
        except (TypeError, ValueError):
            return None, f"Ugyldige tall for tee «{name}»."
    return rows, None


def _apply_tee_rows(course, rows):
    """Create or update tees on a course from parsed rows."""
    for row in rows:
        if row["tee_id"]:
            tee = CourseTee.query.filter_by(id=row["tee_id"], course_id=course.id).first()
            if not tee:
                continue
            tee.name = row["name"]
            tee.gender = row["gender"]
            tee.par = row["par"]
            tee.course_rating = row["course_rating"]
            tee.slope_rating = row["slope_rating"]
        else:
            db.session.add(CourseTee(
                course_id=course.id,
                name=row["name"],
                gender=row["gender"],
                par=row["par"],
                course_rating=row["course_rating"],
                slope_rating=row["slope_rating"],
            ))


def _database_url():
    """Normalize DATABASE_URL for SQLAlchemy (Render still uses postgres://)."""
    url = os.environ.get("DATABASE_URL") or ""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _engine_options(database_url):
    """Engine options that survive Neon/Render idle disconnects."""
    if (database_url or "").startswith("sqlite"):
        # SQLite is the disposable database for local verification.
        # libpq connect args and QueuePool sizing apply only to PostgreSQL.
        return {}

    connect_args = {"connect_timeout": 10}
    is_remote = database_url and not any(
        host in database_url for host in ("localhost", "127.0.0.1")
    )
    if is_remote:
        connect_args.update({
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        })

    options = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }
    if "-pooler" in database_url:
        from sqlalchemy.pool import NullPool
        options["poolclass"] = NullPool
    else:
        options["pool_recycle"] = 280
        options["pool_size"] = 5
        options["max_overflow"] = 2
    return options


def create_app():
    app = Flask(__name__)
    if os.environ.get('FLASK_ENV') != 'production':
        load_dotenv()
    database_url = _database_url()
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or None
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = _engine_options(database_url)
    db.init_app(app)
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if secret_key:
        app.config["SECRET_KEY"] = secret_key
    return app

app = create_app()


def _init_schema():
    """Create tables and apply lightweight column migrations."""
    db.create_all()
    ensure_course_tee_gender_column()


@app.before_request
def ensure_schema():
    """Initialize schema on first request so worker boot is not blocked by the DB."""
    if getattr(app, "_schema_ready", False) or request.path in {"/health", "/"}:
        return
    try:
        _init_schema()
        app._schema_ready = True
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Schema init failed")


@app.route("/health")
def health():
    """Liveness check used by Render; must not depend on the database."""
    return {"status": "ok"}, 200


@app.route("/")
def home():
    return render_template("holding.html")


def _organizer_open():
    return session.get("organizer") is True


def _secret_matches(posted):
    expected = os.environ.get("ORGANIZER_SECRET") or ""
    if not expected or not posted:
        return False
    return hmac.compare_digest(posted, expected)


@app.route("/start", methods=["GET", "POST"])
def start():
    if request.method == "POST" and not _secret_matches(request.form.get("secret") or ""):
        return render_template("organizer.html", organizer=False, rejected=True)
    if request.method == "POST":
        session["organizer"] = True
    if not _organizer_open():
        return render_template("organizer.html", organizer=False, rejected=False)
    groups = Group.query.order_by(Group.id.asc()).all()
    return render_template("organizer.html", organizer=True, groups=groups)


@app.route("/start/groups", methods=["POST"])
def create_group():
    if not _organizer_open():
        return render_template("organizer.html", organizer=False, rejected=False)
    name = (request.form.get("name") or "").strip()
    if not name:
        groups = Group.query.order_by(Group.id.asc()).all()
        return render_template(
            "organizer.html",
            organizer=True,
            groups=groups,
            error="Skriv et gruppenavn.",
        )
    group = Group(name=name)
    db.session.add(group)
    db.session.commit()
    return redirect(url_for("show_group", token=group.token))


def _group_or_404(token):
    group = Group.query.filter_by(token=token).one_or_none()
    if group is None:
        abort(404)
    return group


def _player_or_404(group, player_id):
    player = Player.query.filter_by(id=player_id, group_id=group.id).one_or_none()
    if player is None:
        abort(404)
    return player


def _posted_player():
    name = (request.form.get("name") or "").strip()
    raw = (request.form.get("handicap") or "").strip()
    if not name:
        return name, raw, None, "Skriv et navn."
    try:
        handicap = float(raw.replace(",", "."))
    except ValueError:
        return name, raw, None, "Skriv et handicap."
    return name, raw, handicap, None


@app.route("/g/<token>")
def show_group(token):
    group = _group_or_404(token)
    return render_template("group.html", group=group)


@app.route("/g/<token>/players", methods=["GET", "POST"])
def new_player(token):
    group = _group_or_404(token)
    error = None
    name = ""
    handicap_value = ""
    if request.method == "POST":
        name, handicap_value, handicap, error = _posted_player()
        if error is None:
            try:
                player = Player(name=name, handicap=handicap, group_id=group.id)
            except HandicapError as exc:
                error = str(exc)
            else:
                db.session.add(player)
                db.session.commit()
                return redirect(url_for("show_group", token=group.token))
    return render_template(
        "players.html",
        group=group,
        error=error,
        name=name,
        handicap_value=handicap_value,
    )


@app.route("/g/<token>/players/<int:player_id>", methods=["GET", "POST"])
def edit_player(token, player_id):
    group = _group_or_404(token)
    player = _player_or_404(group, player_id)
    error = None
    name = player.name
    handicap_value = f"{player.handicap:.1f}"
    if request.method == "POST":
        name, handicap_value, handicap, error = _posted_player()
        if error is None:
            try:
                player.change(name, handicap)
            except HandicapError as exc:
                error = str(exc)
            else:
                db.session.commit()
                return redirect(url_for("show_group", token=group.token))
    return render_template(
        "player_form.html",
        group=group,
        player=player,
        error=error,
        name=name,
        handicap_value=handicap_value,
    )


@app.route("/g/<token>/players/<int:player_id>/delete", methods=["POST"])
def delete_player(token, player_id):
    group = _group_or_404(token)
    player = _player_or_404(group, player_id)
    db.session.delete(player)
    db.session.commit()
    return redirect(url_for("show_group", token=group.token))


def _trip_or_404(group, trip_id):
    trip = Trip.query.filter_by(id=trip_id, group_id=group.id).one_or_none()
    if trip is None:
        abort(404)
    return trip


def _round_or_404(trip, round_id):
    golf_round = Round.query.filter_by(id=round_id, trip_id=trip.id).one_or_none()
    if golf_round is None:
        abort(404)
    return golf_round


def _latest_trip(group):
    return (
        Trip.query.filter_by(group_id=group.id)
        .order_by(Trip.created_at.desc(), Trip.id.desc())
        .first()
    )


def _posted_trip_fields():
    name = (request.form.get("name") or "").strip()
    destination = (request.form.get("destination_name") or "").strip()
    yr_raw = (request.form.get("yr_location_id") or "").strip()
    rules = (request.form.get("local_rules") or "").strip()
    error = None
    if not name:
        error = "Skriv et navn."
    elif len(name) > 120:
        error = "Navnet er for langt."
    elif not destination:
        error = "Skriv en destinasjon."
    elif len(destination) > 120:
        error = "Destinasjonen er for lang."
    elif yr_raw and _YR_ID.fullmatch(yr_raw) is None:
        error = "Ugyldig yr-id."
    return name, destination, yr_raw, rules, error


def _checked_players(group):
    selected = []
    for raw in request.form.getlist("player_ids"):
        if str(raw).isdigit():
            selected.append(int(raw))
    if not selected:
        return []
    return (
        Player.query.filter(Player.group_id == group.id, Player.id.in_(selected))
        .order_by(Player.name.asc())
        .all()
    )


def _days_until(trip):
    if not trip.rounds:
        return None
    earliest = min(golf_round.play_date for golf_round in trip.rounds)
    today = date.today()
    if earliest > today:
        return (earliest - today).days
    return None


def _render_trip(group, trip, error, name, destination, yr_raw, rules):
    member_ids = {membership.player_id for membership in trip.memberships}
    return render_template(
        "trip.html",
        group=group,
        trip=trip,
        members=trip.members(),
        available=[player for player in group.players if player.id not in member_ids],
        days_until=_days_until(trip),
        error=error,
        name=name,
        destination_name=destination,
        yr_location_id=yr_raw,
        local_rules=rules,
    )


@app.route("/g/<token>/trips", methods=["GET", "POST"])
def new_trip(token):
    group = _group_or_404(token)
    latest = _latest_trip(group)
    error = None
    name = ""
    destination = ""
    yr_raw = ""
    rules = latest.local_rules if latest is not None else ""
    selected_ids = [player.id for player in group.players]
    if request.method == "POST":
        name, destination, yr_raw, rules, error = _posted_trip_fields()
        selected = _checked_players(group)
        selected_ids = [player.id for player in selected]
        if error is None:
            trip = Trip(
                group_id=group.id,
                name=name,
                destination_name=destination,
                yr_location_id=yr_raw or None,
                local_rules=rules,
            )
            for player in selected:
                trip.memberships.append(TripPlayer(
                    player_id=player.id,
                    handicap=player.handicap,
                ))
            db.session.add(trip)
            db.session.commit()
            return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))
    return render_template(
        "trip_form.html",
        group=group,
        error=error,
        name=name,
        destination_name=destination,
        yr_location_id=yr_raw,
        local_rules=rules,
        selected_ids=selected_ids,
    )


@app.route("/g/<token>/trips/<int:trip_id>", methods=["GET", "POST"])
def show_trip(token, trip_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    if request.method == "POST":
        name, destination, yr_raw, rules, error = _posted_trip_fields()
        if error is None:
            trip.name = name
            trip.destination_name = destination
            trip.yr_location_id = yr_raw or None
            trip.local_rules = rules
            db.session.commit()
            return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))
        return _render_trip(group, trip, error, name, destination, yr_raw, rules)
    return _render_trip(
        group,
        trip,
        None,
        trip.name,
        trip.destination_name,
        trip.yr_location_id or "",
        trip.local_rules or "",
    )


@app.route("/g/<token>/trips/<int:trip_id>/players/<int:player_id>", methods=["POST"])
def join_trip(token, trip_id, player_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    player = _player_or_404(group, player_id)
    already = TripPlayer.query.filter_by(trip_id=trip.id, player_id=player.id).one_or_none()
    if already is None:
        db.session.add(TripPlayer(
            trip_id=trip.id,
            player_id=player.id,
            handicap=player.handicap,
        ))
        db.session.commit()
    return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))


@app.route(
    "/g/<token>/trips/<int:trip_id>/players/<int:player_id>/delete",
    methods=["POST"],
)
def leave_trip(token, trip_id, player_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    player = _player_or_404(group, player_id)
    membership = TripPlayer.query.filter_by(trip_id=trip.id, player_id=player.id).one_or_none()
    if membership is None:
        abort(404)
    db.session.delete(membership)
    db.session.commit()
    return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))


@app.route("/g/<token>/trips/<int:trip_id>/delete", methods=["POST"])
def delete_trip(token, trip_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    for golf_round in list(trip.rounds):
        for score in list(golf_round.scores):
            db.session.delete(score)
    db.session.delete(trip)
    db.session.commit()
    return redirect(url_for("show_group", token=group.token))


def _posted_round():
    course_id = request.form.get("course_id", type=int)
    tee_id = request.form.get("tee_id", type=int)
    play_raw = (request.form.get("play_date") or "").strip()
    tee_time = (request.form.get("tee_time") or "").strip()
    pick_up = (request.form.get("pick_up") or "").strip()
    course = GolfCourse.get_by_id(course_id) if course_id else None
    tee = None
    if course is not None and tee_id:
        tee = CourseTee.query.filter_by(id=tee_id, course_id=course.id).one_or_none()
    played = None
    error = None
    if course is None:
        error = "Velg en bane."
    elif tee is None:
        error = "Velg et tee."
    else:
        try:
            played = datetime.strptime(play_raw, "%Y-%m-%d").date()
        except ValueError:
            error = "Skriv en dato."
    if error is None and _TEE_TIME.fullmatch(tee_time) is None:
        error = "Skriv en teetime."
    if error is None and len(pick_up) > 12:
        error = "Henting kan ikke være lengre enn 12 tegn."
    return course, tee, played, play_raw, tee_time, pick_up, error


def _render_round(group, trip, error, course_id, tee_id, play_raw, tee_time, pick_up, editing):
    return render_template(
        "round_form.html",
        group=group,
        trip=trip,
        courses=GolfCourse.get_all(),
        error=error,
        course_id=course_id,
        tee_id=tee_id,
        play_date=play_raw,
        tee_time=tee_time,
        pick_up=pick_up,
        editing=editing,
    )


@app.route("/g/<token>/trips/<int:trip_id>/rounds", methods=["GET", "POST"])
def new_round(token, trip_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    error = None
    course_id = None
    tee_id = None
    play_raw = ""
    tee_time = ""
    pick_up = ""
    if request.method == "POST":
        course, tee, played, play_raw, tee_time, pick_up, error = _posted_round()
        course_id = course.id if course is not None else request.form.get("course_id", type=int)
        tee_id = tee.id if tee is not None else request.form.get("tee_id", type=int)
        if error is None:
            db.session.add(Round(
                trip_id=trip.id,
                course_id=course.id,
                tee_id=tee.id,
                play_date=played,
                tee_time=tee_time,
                pick_up=pick_up or None,
                kind="oom",
            ))
            db.session.commit()
            return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))
    return _render_round(
        group, trip, error, course_id, tee_id, play_raw, tee_time, pick_up, False,
    )


@app.route("/g/<token>/trips/<int:trip_id>/rounds/<int:round_id>", methods=["GET", "POST"])
def edit_round(token, trip_id, round_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    golf_round = _round_or_404(trip, round_id)
    error = None
    course_id = golf_round.course_id
    tee_id = golf_round.tee_id
    play_raw = golf_round.play_date.isoformat()
    tee_time = golf_round.tee_time
    pick_up = golf_round.pick_up or ""
    if request.method == "POST":
        course, tee, played, play_raw, tee_time, pick_up, error = _posted_round()
        course_id = course.id if course is not None else request.form.get("course_id", type=int)
        tee_id = tee.id if tee is not None else request.form.get("tee_id", type=int)
        if error is None:
            golf_round.course_id = course.id
            golf_round.tee_id = tee.id
            golf_round.play_date = played
            golf_round.tee_time = tee_time
            golf_round.pick_up = pick_up or None
            db.session.commit()
            return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))
    return _render_round(
        group, trip, error, course_id, tee_id, play_raw, tee_time, pick_up, True,
    )


def _oom_rounds(trip):
    return [golf_round for golf_round in trip.rounds if golf_round.kind == "oom"]


def _scores_for(golf_round):
    rows = RoundScore.query.filter_by(round_id=golf_round.id).all()
    return {row.player_id: row.score for row in rows}


def _trip_oom(trip):
    rounds = _oom_rounds(trip)
    found = [_scores_for(golf_round) for golf_round in rounds]
    entries = []
    for membership in trip.members():
        entries.append({
            "name": membership.player.name,
            "scores": [scores.get(membership.player_id) for scores in found],
        })
    return rounds, oom_table(entries)


def _parse_score(raw):
    text = (raw or "").strip()
    if text == "":
        return None
    if not text.isdigit():
        raise ValueError
    score = int(text)
    if score > 200:
        raise ValueError
    return score


def _posted_scores(trip):
    member_ids = {membership.player_id for membership in trip.memberships}
    posted = {}
    for key, value in request.form.items():
        if not key.startswith("score_"):
            continue
        raw_id = key[len("score_"):]
        if not raw_id.isdigit() or int(raw_id) not in member_ids:
            abort(404)
        posted[int(raw_id)] = value
    parsed = {}
    for player_id, raw in posted.items():
        try:
            parsed[player_id] = _parse_score(raw)
        except ValueError:
            return None, "Skriv et heltall fra 0 til 200."
    for membership in trip.memberships:
        parsed.setdefault(membership.player_id, None)
    return parsed, None


def _write_scores(golf_round, parsed):
    for player_id, score in parsed.items():
        existing = RoundScore.query.filter_by(
            round_id=golf_round.id,
            player_id=player_id,
        ).all()
        if score is None:
            for row in existing:
                db.session.delete(row)
            continue
        if existing:
            existing[0].score = score
            for extra in existing[1:]:
                db.session.delete(extra)
        else:
            db.session.add(RoundScore(
                round_id=golf_round.id,
                player_id=player_id,
                score=score,
            ))


def _score_rows(trip, golf_round, values):
    rows = []
    for membership in trip.members():
        player = membership.player
        if values is None:
            stored = _scores_for(golf_round).get(player.id)
            value = "" if stored is None else str(stored)
        else:
            raw = values.get(player.id)
            value = "" if raw is None else str(raw)
        rows.append({"player": player, "value": value})
    return rows


@app.route(
    "/g/<token>/trips/<int:trip_id>/rounds/<int:round_id>/scores",
    methods=["GET", "POST"],
)
def edit_scores(token, trip_id, round_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    golf_round = _round_or_404(trip, round_id)
    error = None
    values = None
    if request.method == "POST":
        parsed, error = _posted_scores(trip)
        if error is None:
            _write_scores(golf_round, parsed)
            db.session.commit()
            return redirect(url_for("show_trip", token=group.token, trip_id=trip.id))
        values = {}
        for membership in trip.memberships:
            values[membership.player_id] = request.form.get(f"score_{membership.player_id}")
    return render_template(
        "scores.html",
        group=group,
        trip=trip,
        golf_round=golf_round,
        rows=_score_rows(trip, golf_round, values),
        error=error,
    )


@app.route("/g/<token>/trips/<int:trip_id>/oom")
def show_oom(token, trip_id):
    group = _group_or_404(token)
    trip = _trip_or_404(group, trip_id)
    rounds, table = _trip_oom(trip)
    return render_template(
        "oom.html",
        group=group,
        trip=trip,
        rounds=rounds,
        table=table,
    )


@app.route("/baner")
def list_golf_courses():
    """List all registered golf courses."""
    courses = GolfCourse.get_all()
    return render_template("list_golf_courses.html", courses=courses)


@app.route("/baner/mottatte-slag")
def list_course_handicaps():
    """Show received strokes per player for a selected course and tee."""
    courses = GolfCourse.get_all()
    course_id = request.args.get("course_id", type=int)
    tee_id = request.args.get("tee_id", type=int)

    selected_course = GolfCourse.get_by_id(course_id) if course_id else None
    selected_tee = None
    player_rows = None

    if selected_course and tee_id:
        selected_tee = CourseTee.query.filter_by(
            id=tee_id, course_id=selected_course.id
        ).first()
        if selected_tee:
            player_rows = [
                {
                    "player": player,
                    "strokes": course_handicap(
                        player.handicap,
                        selected_tee.slope_rating,
                        selected_tee.course_rating,
                        selected_tee.par,
                    ),
                }
                for player in Player.get_all()
            ]

    return render_template(
        "mottatte_slag.html",
        courses=courses,
        selected_course=selected_course,
        selected_tee=selected_tee,
        player_rows=player_rows,
        course_id=course_id,
        tee_id=tee_id,
    )


@app.route("/baner/ny", methods=["GET", "POST"])
def add_golf_course():
    """Register a golf course with tee boxes."""
    error = None
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        facility = (request.form.get("facility") or "").strip()
        rows, parse_error = _parse_tee_rows_from_form(request.form)

        if not name or not facility:
            error = "Banenavn og anlegg må fylles ut."
        elif parse_error:
            error = parse_error
        elif not rows:
            error = "Legg inn minst ett tee-sted."
        else:
            course = GolfCourse(name=name, facility=facility)
            db.session.add(course)
            db.session.flush()
            _apply_tee_rows(course, rows)
            db.session.commit()
            return redirect(url_for("view_golf_course", course_id=course.id))

    return render_template("add_golf_course.html", error=error, tee_genders=TEE_GENDERS)


@app.route("/baner/<int:course_id>", methods=["GET", "POST"])
def view_golf_course(course_id):
    """Show and edit course details and tee data."""
    course = GolfCourse.get_by_id(course_id)
    if not course:
        return redirect(url_for("list_golf_courses"))

    error = None
    message = request.args.get("message")

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        facility = (request.form.get("facility") or "").strip()
        rows, parse_error = _parse_tee_rows_from_form(request.form)

        if not name or not facility:
            error = "Banenavn og anlegg må fylles ut."
        elif parse_error:
            error = parse_error
        elif not rows:
            error = "Banen må ha minst ett tee-sted."
        else:
            course.name = name
            course.facility = facility
            _apply_tee_rows(course, rows)
            db.session.commit()
            return redirect(url_for(
                "view_golf_course",
                course_id=course.id,
                message="Banen er oppdatert.",
            ))

    return render_template(
        "view_golf_course.html",
        course=course,
        course_handicap=course_handicap,
        tee_genders=TEE_GENDERS,
        error=error,
        message=message,
    )


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True)
