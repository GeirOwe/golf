import hmac
import os

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, session, url_for
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import CourseTee, GolfCourse, Group, Player, db
from models import course_handicap


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


@app.route("/g/<token>")
def show_group(token):
    group = Group.query.filter_by(token=token).one_or_none()
    if group is None:
        abort(404)
    return render_template("group.html", group=group)


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
