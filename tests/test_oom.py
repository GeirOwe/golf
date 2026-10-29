import os
import tempfile
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-oom-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db
from database import CourseTee, GolfCourse, Player, Round, RoundScore
from scoring import oom_table


def _use_database(path):
    uri = "sqlite:///" + path.resolve().as_posix()
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SECRET_KEY"] = "verify-flask-secret"
    app._schema_ready = False
    with app.app_context():
        db.session.remove()
        engines = db._app_engines[app]
        current = engines.get(None)
        if current is not None:
            current.dispose()
        engines[None] = create_engine(uri)


def _client(tmp_path):
    _use_database(tmp_path / "golf.db")
    return app.test_client()


def _open_group(client, name):
    opened = client.post("/start/groups", data={"name": name})
    assert opened.status_code == 302
    return opened.headers["Location"]


def _course(name):
    with app.app_context():
        course = GolfCourse(name=name, facility="Lisboa")
        db.session.add(course)
        db.session.flush()
        tee = CourseTee(
            course_id=course.id,
            name="Blå",
            gender="Herre",
            par=72,
            course_rating=71.2,
            slope_rating=125,
        )
        db.session.add(tee)
        db.session.commit()
        return course.id, tee.id


def test_oom_table_drops_zero_and_ranks_ties_by_name():
    table = oom_table([
        {"name": "Ada", "scores": [36, 0]},
        {"name": "Bo", "scores": [30, None]},
        {"name": "Cia", "scores": [30]},
        {"name": "Nia", "scores": [0, None]},
    ])
    by_name = {row["name"]: row for row in table}
    assert [row["name"] for row in table] == ["Ada", "Bo", "Cia"]
    assert by_name["Ada"]["total"] == 36
    assert by_name["Ada"]["snitt"] == 36.0
    assert by_name["Ada"]["rank"] == 1
    assert by_name["Ada"]["bonus"] == 4
    assert by_name["Bo"]["rank"] == 2
    assert by_name["Bo"]["bonus"] == 3
    assert by_name["Cia"]["rank"] == 3
    assert by_name["Cia"]["bonus"] == 2
    assert "Nia" not in by_name
    tied = oom_table([
        {"name": "Cia", "scores": [30]},
        {"name": "Bo", "scores": [30]},
    ])
    assert [(row["name"], row["rank"]) for row in tied] == [("Bo", 1), ("Cia", 2)]

    five = oom_table([
        {"name": "Ada", "scores": [10]},
        {"name": "Bo", "scores": [9]},
        {"name": "Cia", "scores": [8]},
        {"name": "Dag", "scores": [7]},
        {"name": "Eli", "scores": [6]},
    ])
    assert [row["bonus"] for row in five] == [4, 3, 2, 1, 0]
    two = oom_table([{"name": "Ada", "scores": [22, 20]}])
    assert two[0]["total"] == 42
    assert two[0]["snitt"] == 21.0


def test_scores_feed_the_trip_table_and_ignore_other_rounds(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    lisboa = _open_group(client, "Lisboa")
    algarve = _open_group(client, "Algarve")
    for name, handicap in (("Ada", "12.4"), ("Bo", "8"), ("Cia", "3")):
        assert client.post(
            lisboa + "/players",
            data={"name": name, "handicap": handicap},
        ).status_code == 302
    with app.app_context():
        players = {player.name: player.id for player in Player.query.all()}
    created = client.post(
        lisboa + "/trips",
        data={
            "name": "Høst 2026",
            "destination_name": "Lisboa",
            "player_ids": [players["Ada"], players["Bo"]],
        },
    )
    trip = created.headers["Location"]
    course_id, tee_id = _course("Verify Hills")
    played = date.today().isoformat()

    def add_round():
        saved = client.post(
            trip + "/rounds",
            data={
                "course_id": course_id,
                "tee_id": tee_id,
                "play_date": played,
                "tee_time": "09:30",
                "pick_up": "Sandvika",
            },
        )
        assert saved.status_code == 302
        with app.app_context():
            return Round.query.order_by(Round.id.desc()).first().id

    first = add_round()
    second = add_round()
    empty_rounds = client.get(trip).get_data(as_text=True)
    assert empty_rounds.count("btn btn--small btn--ghost") == 2
    assert "btn btn--small btn--primary" not in empty_rounds
    form = client.get(f"{trip}/rounds/{first}/scores")
    form_body = form.get_data(as_text=True)
    assert form.status_code == 200
    assert "<h1>Registrer score</h1>" in form_body
    assert "Ada" in form_body
    assert "Bo" in form_body
    assert "Cia" not in form_body
    assert "<title>Høst 2026</title>" in form_body
    other = f"{algarve}/trips/{trip.rsplit('/', 1)[-1]}/rounds/{first}/scores"
    assert client.get(other).status_code == 404

    saved = client.post(
        f"{trip}/rounds/{first}/scores",
        data={f"score_{players['Ada']}": "36", f"score_{players['Bo']}": "30"},
        follow_redirects=True,
    )
    saved_body = saved.get_data(as_text=True)
    assert "09:30" in saved_body
    assert saved_body.count("btn btn--small btn--primary") == 1
    assert saved_body.count("btn btn--small btn--ghost") == 1
    oom = client.get(trip + "/oom")
    oom_body = oom.get_data(as_text=True)
    assert "<h1>Tabell OOM</h1>" in oom_body
    assert "sheet__day" in oom_body
    weekday = ("man", "tir", "ons", "tor", "fre", "lør", "søn")[date.today().weekday()]
    assert f'class="sheet__day">{weekday}</span>' in oom_body
    assert date.today().strftime("%d.%m") in oom_body
    assert "Total" in oom_body
    assert "Snitt" in oom_body
    assert "36.0" in oom_body
    assert oom_body.index("Ada") < oom_body.index("Bo")

    edited = client.post(
        f"{trip}/rounds/{first}/scores",
        data={f"score_{players['Ada']}": "40", f"score_{players['Bo']}": "30"},
        follow_redirects=True,
    )
    assert edited.status_code == 200
    changed = client.get(trip + "/oom").get_data(as_text=True)
    assert "40" in changed
    assert "36" not in changed

    client.post(
        f"{trip}/rounds/{first}/scores",
        data={f"score_{players['Ada']}": "36", f"score_{players['Bo']}": "0"},
    )
    zeros = client.get(trip + "/oom").get_data(as_text=True)
    assert "Bo" not in zeros
    assert "36" in zeros
    with app.app_context():
        stored = RoundScore.query.filter_by(player_id=players["Bo"]).one()
        assert stored.score == 0

    client.post(
        f"{trip}/rounds/{first}/scores",
        data={f"score_{players['Ada']}": "36", f"score_{players['Bo']}": ""},
    )
    cleared = client.get(trip + "/oom").get_data(as_text=True)
    assert "Bo" not in cleared
    with app.app_context():
        assert RoundScore.query.filter_by(player_id=players["Bo"]).one_or_none() is None

    rejected = client.post(
        f"{trip}/rounds/{first}/scores",
        data={f"score_{players['Ada']}": "36", f"score_{players['Cia']}": "20"},
    )
    assert rejected.status_code == 404
    assert "36" in client.get(trip + "/oom").get_data(as_text=True)

    client.post(
        f"{trip}/rounds/{first}/scores",
        data={f"score_{players['Ada']}": "22", f"score_{players['Bo']}": ""},
    )
    client.post(
        f"{trip}/rounds/{second}/scores",
        data={f"score_{players['Ada']}": "20", f"score_{players['Bo']}": ""},
    )
    both = client.get(trip + "/oom").get_data(as_text=True)
    assert "42" in both
    assert "21.0" in both

    with app.app_context():
        finale = db.session.get(Round, second)
        finale.kind = "finale"
        db.session.commit()
    only_oom = client.get(trip + "/oom").get_data(as_text=True)
    assert "42" not in only_oom
    assert "21.0" not in only_oom
    assert "22.0" in only_oom
    odd = client.post(f"{trip}/rounds/{first}/scores", data={"score_²": "10"})
    assert odd.status_code == 404


def test_duplicate_round_scores_collapse_before_the_unique_index(tmp_path):
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import IntegrityError

    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    client.post("/start/groups", data={"name": "Fjord"})
    with app.app_context():
        db.session.execute(text("ALTER TABLE round_scores RENAME TO round_scores_old"))
        db.session.execute(text(
            "CREATE TABLE round_scores ("
            "id INTEGER NOT NULL PRIMARY KEY, "
            "round_id INTEGER NOT NULL, "
            "player_id INTEGER NOT NULL, "
            "score INTEGER, "
            "created_at DATETIME)"
        ))
        db.session.execute(text(
            "INSERT INTO round_scores (id, round_id, player_id, score) "
            "VALUES (1, 1, 1, 10), (2, 1, 1, 36)"
        ))
        db.session.execute(text("DROP TABLE round_scores_old"))
        db.session.commit()
        app._schema_ready = False
    assert client.get("/start").status_code == 200
    with app.app_context():
        rows = db.session.execute(text(
            "SELECT score FROM round_scores ORDER BY id"
        )).all()
        names = {
            constraint["name"]
            for constraint in inspect(db.session.get_bind()).get_unique_constraints("round_scores")
        }
        names.update(
            index["name"]
            for index in inspect(db.session.get_bind()).get_indexes("round_scores")
        )
        failed = False
        try:
            db.session.execute(text(
                "INSERT INTO round_scores (round_id, player_id, score) VALUES (1, 1, 5)"
            ))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            failed = True
    assert rows == [(36,)]
    assert failed is True
    assert "uq_round_player_score" in names
