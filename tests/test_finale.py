import os
import tempfile
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-finale-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db
from database import CourseTee, GolfCourse, Player, Round, TripPlayer
from scoring import finale_table


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


def _course():
    with app.app_context():
        course = GolfCourse(name="Verify Hills", facility="Lisboa")
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


def _round_fields(course_id, tee_id, kind):
    return {
        "course_id": course_id,
        "tee_id": tee_id,
        "play_date": date.today().isoformat(),
        "tee_time": "09:30",
        "pick_up": "Sandvika",
        "kind": kind,
    }


def test_finale_table_shares_a_place_and_adds_the_bonus():
    table = finale_table([
        {"name": "Cia", "score": 20, "bonus": 0},
        {"name": "Bo", "score": 30, "bonus": 4},
        {"name": "Ada", "score": 30, "bonus": 4},
        {"name": "Dag", "score": None, "bonus": 2},
    ])
    assert [(row["name"], row["total"], row["place"]) for row in table] == [
        ("Ada", 34, 1),
        ("Bo", 34, 1),
        ("Cia", 20, 2),
        ("Dag", 2, None),
    ]


def test_finale_bonus_locks_and_the_finale_round_stays_out_of_oom(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    lisboa = _open_group(client, "Lisboa")
    algarve = _open_group(client, "Algarve")
    for name, handicap in (("Ada", "12.4"), ("Bo", "8"), ("Cia", "3"), ("Dag", "5")):
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
            "player_ids": [players["Ada"], players["Bo"], players["Cia"]],
        },
    )
    trip = created.headers["Location"]
    course_id, tee_id = _course()
    played = client.post(trip + "/rounds", data=_round_fields(course_id, tee_id, "oom"))
    assert played.status_code == 302
    with app.app_context():
        first = Round.query.one().id
    client.post(
        f"{trip}/rounds/{first}/scores",
        data={
            f"score_{players['Ada']}": "36",
            f"score_{players['Bo']}": "",
            f"score_{players['Cia']}": "",
        },
    )
    assert "36" in client.get(trip + "/oom").get_data(as_text=True)

    client.post(f"{trip}/rounds/{first}", data=_round_fields(course_id, tee_id, "finale"))
    excluded = client.get(trip + "/oom").get_data(as_text=True)
    assert "36" not in excluded
    assert "Ingen scorer registrert ennå." in excluded
    client.post(f"{trip}/rounds/{first}", data=_round_fields(course_id, tee_id, "oom"))
    assert "36" in client.get(trip + "/oom").get_data(as_text=True)

    finale = client.post(trip + "/rounds", data=_round_fields(course_id, tee_id, "finale"))
    assert finale.status_code == 302
    rejected = client.post(trip + "/rounds", data=_round_fields(course_id, tee_id, "finale"))
    assert "Turen har allerede en finale." in rejected.get_data(as_text=True)
    with app.app_context():
        assert Round.query.filter_by(kind="finale").count() == 1

    empty = client.post(
        lisboa + "/trips",
        data={"name": "Høst 2027", "destination_name": "Lisboa", "player_ids": [players["Ada"]]},
    )
    quiet = client.get(empty.headers["Location"] + "/finale").get_data(as_text=True)
    assert "Ingen finale ennå." in quiet
    assert "Total" not in quiet

    live = client.get(trip + "/finale").get_data(as_text=True)
    ada_at = live.index(">Ada</label>")
    bo_at = live.index(">Bo</label>")
    assert "Bonus 4" in live[ada_at:bo_at]
    client.post(
        f"{trip}/rounds/{first}/scores",
        data={
            f"score_{players['Ada']}": "36",
            f"score_{players['Bo']}": "40",
            f"score_{players['Cia']}": "",
        },
    )
    changed = client.get(trip + "/finale").get_data(as_text=True)
    ada_at = changed.index(">Ada</label>")
    bo_at = changed.index(">Bo</label>")
    cia_at = changed.index(">Cia</label>")
    assert "Bonus 3" in changed[ada_at:bo_at]
    assert "Bonus 4" in changed[bo_at:cia_at]
    client.post(
        f"{trip}/rounds/{first}/scores",
        data={
            f"score_{players['Ada']}": "36",
            f"score_{players['Bo']}": "",
            f"score_{players['Cia']}": "",
        },
    )

    saved = client.post(
        trip + "/finale",
        data={
            f"score_{players['Ada']}": "30",
            f"score_{players['Bo']}": "",
            f"score_{players['Cia']}": "",
        },
        follow_redirects=True,
    )
    saved_body = saved.get_data(as_text=True)
    assert "<h1>Finaleresultat</h1>" in saved_body
    ada_total = (
        "<td class=\"num\">4</td>\n"
        "        <td class=\"num\">30</td>\n"
        "        <td class=\"num\">34</td>"
    )
    assert "<td></td>\n        <td>Bo</td>" in saved_body
    assert ada_total in saved_body
    trip_id = int(trip.rsplit("/", 1)[-1])
    with app.app_context():
        rows = TripPlayer.query.filter_by(trip_id=trip_id).all()
        stored = {row.player.name: row.finale_bonus for row in rows}
    assert stored["Ada"] == 4
    assert stored["Bo"] == 0
    assert stored["Cia"] == 0

    client.post(
        f"{trip}/rounds/{first}/scores",
        data={
            f"score_{players['Ada']}": "10",
            f"score_{players['Bo']}": "50",
            f"score_{players['Cia']}": "",
        },
    )
    locked = client.get(trip + "/finale/resultat").get_data(as_text=True)
    assert ada_total in locked
    oom = client.get(trip + "/oom").get_data(as_text=True)
    assert "10.0" in oom
    assert "50.0" in oom
    assert "20.0" not in oom

    client.post(
        trip + "/finale",
        data={
            f"score_{players['Ada']}": "30",
            f"score_{players['Bo']}": "34",
            f"score_{players['Cia']}": "20",
        },
    )
    placed = client.get(trip + "/finale/resultat").get_data(as_text=True)
    assert "1</td>\n        <td>Ada</td>" in placed
    assert "1</td>\n        <td>Bo</td>" in placed
    assert "2</td>\n        <td>Cia</td>" in placed

    joined = client.post(f"{trip}/players/{players['Dag']}")
    assert joined.status_code == 302
    with app.app_context():
        dag = TripPlayer.query.filter_by(player_id=players["Dag"]).one()
        assert dag.finale_bonus == 0

    other = f"{algarve}/trips/{trip.rsplit('/', 1)[-1]}/finale"
    assert client.post(other, data={f"score_{players['Ada']}": "30"}).status_code == 404
