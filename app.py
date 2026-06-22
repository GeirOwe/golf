"""
Golf Application
---------------
A Flask web application for managing golf players and rounds.
Deployed on Render.com: https://golf-app-w497.onrender.com
"""

import os
from datetime import datetime, date
import locale
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask, render_template, request, redirect, url_for
from database import db, Player, Round, RoundScore, FinaleScore, GolfCourse, CourseTee
from models import HandicapError, course_handicap
from dotenv import load_dotenv
from openai import OpenAI

# Set Norwegian locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, 'nb_NO.UTF-8')
except locale.Error:
    # Fallback if Norwegian locale is not available
    locale.setlocale(locale.LC_TIME, '')

# Norwegian weekday names (index 0 = Monday), for display when server locale is not Norwegian
WEEKDAYS_NO = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag']

def format_date_norwegian(dt):
    """Return date string with Norwegian weekday and dd.mm, e.g. 'Mandag 10.03'."""
    return f"{WEEKDAYS_NO[dt.weekday()]} {dt.strftime('%d.%m')}"


def get_oom_bonus_by_player_id(players):
    """Return bonus points based on OOM rank (1-4 => 4/3/2/1)."""
    oom_rows = []
    for player in players:
        scores = RoundScore.query.filter_by(player_id=player.id).all()
        valid_scores = [score.score for score in scores if score.score]
        if not valid_scores:
            continue
        oom_rows.append({
            "player_id": player.id,
            "total": sum(valid_scores),
            "name": player.name
        })

    # Deterministic sort for tie handling
    oom_rows.sort(key=lambda row: (-row["total"], row["name"]))

    bonus_scale = [4, 3, 2, 1]
    bonus_by_player_id = {player.id: 0 for player in players}
    rank_by_player_id = {}

    for idx, row in enumerate(oom_rows, start=1):
        rank_by_player_id[row["player_id"]] = idx
        if idx <= 4:
            bonus_by_player_id[row["player_id"]] = bonus_scale[idx - 1]

    return bonus_by_player_id, rank_by_player_id


def finale_has_started():
    """True once at least one finale score has been saved."""
    return FinaleScore.query.filter(FinaleScore.score.isnot(None)).count() > 0


def sync_locked_finale_bonus(players):
    """Snapshot current OOM bonus for all players when finale starts."""
    bonus_by_player_id, _ = get_oom_bonus_by_player_id(players)
    for player in players:
        row = FinaleScore.query.filter_by(player_id=player.id).first()
        bonus = bonus_by_player_id.get(player.id, 0)
        if row:
            row.bonus = bonus
        else:
            db.session.add(FinaleScore(
                player_id=player.id,
                bonus=bonus,
                score=None
            ))


def build_finale_rows(players):
    """Build finale rows; bonus follows live OOM until the first finale score is saved."""
    live_bonus_by_player_id, rank_by_player_id = get_oom_bonus_by_player_id(players)
    finale_score_rows = FinaleScore.query.all()
    finale_scores_by_player_id = {row.player_id: row for row in finale_score_rows}
    use_locked_bonus = finale_has_started()

    finale_rows = []
    for player in players:
        stored = finale_scores_by_player_id.get(player.id)
        if use_locked_bonus:
            bonus = stored.bonus if stored else live_bonus_by_player_id.get(player.id, 0)
        else:
            bonus = live_bonus_by_player_id.get(player.id, 0)
        finale_score = stored.score if stored else None
        total = (finale_score if finale_score is not None else 0) + bonus
        finale_rows.append({
            "player_id": player.id,
            "name": player.name,
            "oom_rank": rank_by_player_id.get(player.id, "-"),
            "bonus": bonus,
            "finale_score": finale_score,
            "total": total
        })

    # Players with score first, then by total desc, then name
    finale_rows.sort(key=lambda row: (row["finale_score"] is None, -row["total"], row["name"]))

    place = 0
    previous_total = None
    for row in finale_rows:
        if row["finale_score"] is None:
            row["place"] = None
            continue
        if row["total"] != previous_total:
            place += 1
            previous_total = row["total"]
        row["place"] = place

    return finale_rows


def ensure_finale_bonus_column():
    """Add finale_scores.bonus for existing databases missing this column."""
    try:
        db.session.execute(text(
            "ALTER TABLE finale_scores ADD COLUMN IF NOT EXISTS bonus INTEGER DEFAULT 0"
        ))
        db.session.commit()
    except SQLAlchemyError:
        # Safety fallback: if table does not exist yet (or DB does not support this DDL),
        # continue startup and let create_all/model usage handle table creation.
        db.session.rollback()


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

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Environment Configuration
    if os.environ.get('FLASK_ENV') != 'production':
        load_dotenv()
    
    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    return app

# Initialize application
app = create_app()

# Ensure database tables exist
with app.app_context():
    db.create_all()
    ensure_finale_bonus_column()
    ensure_course_tee_gender_column()

# Basic Routes
@app.route("/")
def home():
    """Display home page with countdown to first tee time."""
    first_round = Round.query.order_by(Round.play_date.asc()).first()
    days_until = None
    if first_round:
        today = date.today()
        tournament_date = first_round.play_date.date()
        if tournament_date > today:
            days_until = (tournament_date - today).days
    
    return render_template("home.html", days_until=days_until)

# Player Management Routes
@app.route("/register", methods=["GET"])
def register_player():
    """Display the player registration form."""
    return render_template("register_player.html")

@app.route("/add_player", methods=["POST"])
def add_player():
    """Handle new player registration with handicap validation."""
    player_name = request.form.get("player_name")
    handicap = float(request.form.get("handicap", 0))
    
    try:
        if player_name:
            player = Player(name=player_name, handicap=handicap)
            db.session.add(player)
            db.session.commit()
            return redirect(url_for("home"))
    except HandicapError as e:
        return render_template("register_player.html", error=str(e))
    
    return redirect(url_for("home"))

@app.route("/players", methods=["GET"])
def list_players():
    """Display list of all players sorted by name."""
    players = Player.get_all()
    return render_template("list_players.html", players=players)

@app.route("/player/<int:player_id>/delete", methods=["POST"])
def delete_player(player_id):
    """Delete a player."""
    player = Player.get_by_id(player_id)
    if player:
        player.delete()
    return redirect(url_for("list_players"))

@app.route("/player/<int:player_id>/update", methods=["GET", "POST"])
def update_player(player_id):
    """Update a player's information with handicap validation."""
    player = Player.get_by_id(player_id)
    if not player:
        return redirect(url_for("list_players"))
    
    if request.method == "POST":
        new_handicap = float(request.form.get("handicap", player.handicap))
        if new_handicap > Player.MAX_HANDICAP:
            return render_template("update_player.html",
                    player=player,
                    error=f"Handicap cannot be greater than {Player.MAX_HANDICAP}")
        
        player.name = request.form.get("player_name", player.name)
        player.handicap = new_handicap
        db.session.commit()
        return redirect(url_for("list_players"))
        
    return render_template("update_player.html", player=player)

# Round Management Routes
@app.route("/rounds")
def list_rounds():
    """Display list of all rounds sorted by date."""
    rounds = Round.get_all()
    for r in rounds:
        r.display_date = format_date_norwegian(r.play_date)
    return render_template("list_rounds.html", rounds=rounds)

@app.route("/round/new", methods=["GET", "POST"])
def add_round():
    """Handle new round registration."""
    if request.method == "POST":
        course_name = request.form.get("course_name")
        play_date = datetime.strptime(request.form.get("play_date"), "%Y-%m-%d")
        tee_time = request.form.get("tee_time")
        pick_up = request.form.get("pick_up")
        
        if course_name and play_date and tee_time:
            round = Round(
                course_name=course_name,
                play_date=play_date,
                tee_time=tee_time,
                pick_up=pick_up
            )
            db.session.add(round)
            db.session.commit()
            return redirect(url_for("list_rounds"))
    
    return render_template("add_round.html")

@app.route("/round/<int:round_id>/delete", methods=["POST"])
def delete_round(round_id):
    """Delete a round."""
    round = Round.get_by_id(round_id)
    if round:
        round.delete()
    return redirect(url_for("list_rounds"))

@app.route("/round/<int:round_id>/update", methods=["GET", "POST"])
def update_round(round_id):
    """Update a round's information."""
    round = Round.get_by_id(round_id)
    if not round:
        return redirect(url_for("list_rounds"))
    
    if request.method == "POST":
        round.course_name = request.form.get("course_name", round.course_name)
        play_date = request.form.get("play_date")
        if play_date:
            round.play_date = datetime.strptime(play_date, "%Y-%m-%d")
        round.tee_time = request.form.get("tee_time", round.tee_time)
        db.session.commit()
        return redirect(url_for("list_rounds"))
        
    return render_template("update_round.html", round=round)

@app.route("/round/<int:round_id>/scores", methods=["GET", "POST"])
def manage_scores(round_id):
    """Manage scores for a round."""
    round = Round.get_by_id(round_id)
    if not round:
        return redirect(url_for("list_rounds"))
    
    players = Player.get_all()
    
    if request.method == "POST":
        # Update scores
        for player in players:
            score = request.form.get(f"score_{player.id}")
            if score:
                # Update or create score
                round_score = RoundScore.query.filter_by(
                    round_id=round.id,
                    player_id=player.id
                ).first()
                
                if round_score:
                    round_score.score = int(score)
                else:
                    round_score = RoundScore(
                        round_id=round.id,
                        player_id=player.id,
                        score=int(score)
                    )
                    db.session.add(round_score)
        
        db.session.commit()
        return redirect(url_for("list_rounds"))
    
    return render_template("manage_scores.html", round=round, players=players)

@app.route("/scores")
def list_scores():
    """Display player scores sorted by total score."""
    players = Player.get_all()
    
    # Get scores for each player
    player_scores = []
    for player in players:
        scores = RoundScore.query.filter_by(player_id=player.id).all()
        if scores:
            # Filter out zeros and empty scores
            valid_scores = [score.score for score in scores if score.score]
            if valid_scores:  # Only process if there are valid scores
                total_score = sum(valid_scores)
                avg_score = round(total_score / len(valid_scores), 1)
                player_scores.append({
                    'name': player.name,
                    'total': total_score,
                    'avg': avg_score,
                    'scores': valid_scores
                })
    
    # Sort by total score descending
    player_scores.sort(key=lambda x: x['total'], reverse=True)
    
    return render_template("list_scores.html", player_scores=player_scores)

@app.route("/scores/reset", methods=["POST"])
def reset_scores():
    """Delete all registered scores."""
    try:
        RoundScore.query.delete()
        FinaleScore.query.delete()
        db.session.commit()
        return redirect(url_for("list_scores", message="Alle scorer er slettet"))
    except Exception as e:
        return redirect(url_for("list_scores", error=f"Kunne ikke slette scorer: {str(e)}"))


@app.route("/finale/reset", methods=["POST"])
def reset_finale_scores():
    """Delete all finale scores and locked bonus for a new tournament."""
    try:
        FinaleScore.query.delete()
        db.session.commit()
        return redirect(url_for("finale", message="Alle finalescorer er slettet"))
    except Exception as e:
        return redirect(url_for("finale", error=f"Kunne ikke slette finalescorer: {str(e)}"))


@app.route("/finale", methods=["GET", "POST"])
def finale():
    """Register finale scores and calculate total with OOM bonus."""
    players = Player.get_all()

    if request.method == "POST":
        scores_to_save = []
        for player in players:
            score_input = request.form.get(f"finale_score_{player.id}", "").strip()
            if score_input == "":
                continue
            try:
                scores_to_save.append((player, int(score_input)))
            except ValueError:
                continue

        if scores_to_save and not finale_has_started():
            sync_locked_finale_bonus(players)

        for player, value in scores_to_save:
            finale_score = FinaleScore.query.filter_by(player_id=player.id).first()
            if finale_score:
                finale_score.score = value
            else:
                bonus_by_player_id, _ = get_oom_bonus_by_player_id(players)
                db.session.add(FinaleScore(
                    player_id=player.id,
                    bonus=bonus_by_player_id.get(player.id, 0),
                    score=value
                ))

        db.session.commit()
        return redirect(url_for("finale"))

    finale_rows = build_finale_rows(players)

    return render_template(
        "finale.html",
        finale_rows=finale_rows,
        message=request.args.get("message"),
        error=request.args.get("error"),
    )


@app.route("/finale/resultat")
def finale_resultat():
    """Show read-only final result table."""
    players = Player.get_all()
    finale_rows = build_finale_rows(players)
    ranked_rows = [row for row in finale_rows if row["finale_score"] is not None]
    return render_template("finale_resultat.html", finale_rows=ranked_rows)

@app.route("/admin/db/reset", methods=["POST"])
def reset_database():
    """Reset and reinitialize the database."""
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
        return redirect(url_for("home", message="Database reset successfully"))
    except Exception as e:
        return redirect(url_for("home", error=f"Database reset failed: {str(e)}"))

@app.route("/flights")
def show_flights():
    """Display the flight setup for each day."""
    return render_template("flight_setup.html")


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


@app.route("/local-rules")
def show_local_rules():
    """Display the local rules for the tournament."""
    return render_template("local_rules.html")

@app.route("/ai-story")
def unicorn_story():
    """Generate and display an AI story."""
    story = None
    error = None
    try:
        XAI_API_KEY = os.getenv("XAI_API_KEY")
        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        completion = client.chat.completions.create(
            model="grok-3-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a pro golfer, quite sarcastic, you stick to one or two sentence answers, ending with an emoji."
                },
                {
                    "role": "user",
                    "content": "What should I do to improve my golf - I am just all over the place and I guess the two beers didnt help :-)"
                },
            ],
        )
        story = completion.choices[0].message.content
    except Exception as e:
        error = f"Feil ved henting av AI-historie: {str(e)}"
    return render_template("unicorn_story.html", story=story, error=error)

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html'), 500

# Run application
if __name__ == "__main__":
    app.run(debug=True)
