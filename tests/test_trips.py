import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-trips-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db
from database import CourseTee, GolfCourse, Player, Round, Trip, TripPlayer


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


def _players(names):
    with app.app_context():
        rows = Player.query.filter(Player.name.in_(names)).all()
    return {player.name: player for player in rows}


def _chrome(body, name):
    assert f"<title>{name}</title>" in body
    assert f'<a class="brand" href="/">{name}</a>' in body
    assert f"<p>{name}</p>" in body


def test_new_trip_keeps_unchecked_players_and_earlier_rounds(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    lisboa = _open_group(client, "Lisboa")
    algarve = _open_group(client, "Algarve")
    for name, handicap in (("Ada", "12.4"), ("Bo", "8"), ("Cia", "3")):
        saved = client.post(
            lisboa + "/players",
            data={"name": name, "handicap": handicap},
        )
        assert saved.status_code == 302

    players = _players(["Ada", "Bo", "Cia"])
    form = client.get(lisboa + "/trips")
    form_body = form.get_data(as_text=True)
    assert form.status_code == 200
    _chrome(form_body, "Lisboa")
    assert form_body.count('name="player_ids"') == 3
    assert form_body.count(" checked") == 3

    rejected = client.post(lisboa + "/trips", data={"name": "   ", "destination_name": "Lisboa"})
    assert "Skriv et navn." in rejected.get_data(as_text=True)
    bad_yr = client.post(
        lisboa + "/trips",
        data={"name": "Høst 2026", "destination_name": "Lisboa", "yr_location_id": "lisboa/1"},
    )
    assert "Ugyldig yr-id." in bad_yr.get_data(as_text=True)

    created = client.post(
        lisboa + "/trips",
        data={
            "name": "Høst 2026",
            "destination_name": "Lisboa",
            "yr_location_id": "2-2267057",
            "player_ids": [players["Ada"].id, players["Bo"].id],
        },
    )
    assert created.status_code == 302
    host = created.headers["Location"]
    page = client.get(host)
    body = page.get_data(as_text=True)
    assert page.status_code == 200
    _chrome(body, "Høst 2026")
    assert "Ada" in body
    assert "12.4" in body
    assert "Bo" in body
    assert "8.0" in body
    assert "Fjern Cia" not in body
    assert "Legg til Cia" in body
    assert "2-2267057" in body
    assert "https://www.yr.no/nb/innhold/2-2267057/meteogram.svg" in body
    assert "Ingen golfrunder registrert ennå." in body

    with app.app_context():
        cia_membership = TripPlayer.query.filter_by(player_id=players["Cia"].id).one_or_none()
        cia = db.session.get(Player, players["Cia"].id)
    assert cia_membership is None
    assert cia is not None
    assert cia.name == "Cia"

    played = date.today() + timedelta(days=10)
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
        course_id = course.id
        tee_id = tee.id

    saved_round = client.post(
        host + "/rounds",
        data={
            "course_id": course_id,
            "tee_id": tee_id,
            "play_date": played.isoformat(),
            "tee_time": "09:30",
            "pick_up": "Sandvika",
        },
        follow_redirects=True,
    )
    round_body = saved_round.get_data(as_text=True)
    assert "Verify Hills" in round_body
    assert "Blå" in round_body
    assert "09:30" in round_body
    assert "Sandvika" in round_body
    assert "10 dager til tee-off" in round_body
    with app.app_context():
        first_round = Round.query.one()
        assert first_round.kind == "oom"
        assert first_round.display_date in round_body
        first_round_id = first_round.id

    edited = client.post(
        f"{host}/rounds/{first_round_id}",
        data={
            "course_id": course_id,
            "tee_id": tee_id,
            "play_date": played.isoformat(),
            "tee_time": "10:00",
            "pick_up": "Sandvika",
        },
        follow_redirects=True,
    )
    assert "10:00" in edited.get_data(as_text=True)
    assert "Sandvika" in edited.get_data(as_text=True)

    ruled = client.post(
        host,
        data={
            "name": "Høst 2026",
            "destination_name": "Lisboa",
            "yr_location_id": "2-2267057",
            "local_rules": "Mulligan på hull 1.",
        },
        follow_redirects=True,
    )
    assert "Mulligan på hull 1." in ruled.get_data(as_text=True)
    assert "Ada" in ruled.get_data(as_text=True)

    second_form = client.get(lisboa + "/trips").get_data(as_text=True)
    assert "Mulligan på hull 1." in second_form
    assert second_form.count(" checked") == 3
    second = client.post(
        lisboa + "/trips",
        data={
            "name": "Høst 2027",
            "destination_name": "Lisboa",
            "yr_location_id": "2-2267057",
            "local_rules": "Mulligan på hull 1.",
            "player_ids": [players["Ada"].id, players["Bo"].id, players["Cia"].id],
        },
    )
    assert second.status_code == 302
    second_body = client.get(second.headers["Location"]).get_data(as_text=True)
    assert "Mulligan på hull 1." in second_body
    _chrome(second_body, "Høst 2027")
    with app.app_context():
        kept = db.session.get(Round, first_round_id)
        assert kept is not None
        assert kept.tee_time == "10:00"
        assert Trip.query.filter_by(name="Høst 2026").one().rounds

    group_body = client.get(lisboa).get_data(as_text=True)
    assert "Høst 2026" in group_body
    assert "Høst 2027" in group_body
    assert "Ingen turer ennå." not in group_body
    _chrome(group_body, "Lisboa")
    algarve_body = client.get(algarve).get_data(as_text=True)
    assert "Høst 2026" not in algarve_body
    assert "Høst 2027" not in algarve_body
    assert "Ingen turer ennå." in algarve_body
    assert client.get(f"{algarve}/trips/{host.rsplit('/', 1)[-1]}").status_code == 404

    thrown = client.post(
        lisboa + "/trips",
        data={"name": "Slett meg", "destination_name": "Lisboa", "player_ids": [players["Ada"].id]},
    )
    removed = client.post(thrown.headers["Location"] + "/delete", follow_redirects=True)
    removed_body = removed.get_data(as_text=True)
    assert "Slett meg" not in removed_body
    assert "Høst 2026" in removed_body
    with app.app_context():
        assert db.session.get(Round, first_round_id) is not None
        assert Trip.query.filter_by(name="Slett meg").one_or_none() is None


def test_trip_stores_its_own_handicap_snapshot(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    lisboa = _open_group(client, "Lisboa")
    client.post(lisboa + "/players", data={"name": "Ada", "handicap": "12.4"})
    client.post(lisboa + "/players", data={"name": "Bo", "handicap": "8"})
    players = _players(["Ada", "Bo"])
    created = client.post(
        lisboa + "/trips",
        data={
            "name": "Høst 2026",
            "destination_name": "Lisboa",
            "player_ids": [players["Ada"].id, players["Bo"].id],
        },
    )
    trip = created.headers["Location"]
    edited = client.post(
        f"{lisboa}/players/{players['Ada'].id}",
        data={"name": "Ada", "handicap": "18.2"},
        follow_redirects=True,
    )
    assert "18.2" in edited.get_data(as_text=True)
    kept = client.get(trip).get_data(as_text=True)
    assert "12.4" in kept
    assert "18.2" not in kept
    with app.app_context():
        snapshot = TripPlayer.query.filter_by(player_id=players["Ada"].id).one()
        assert snapshot.handicap == 12.4

    client.post(f"{trip}/players/{players['Bo'].id}/delete")
    group_body = client.get(lisboa).get_data(as_text=True)
    assert "Bo" in group_body
    away = client.get(trip).get_data(as_text=True)
    assert "Fjern Bo" not in away
    assert "Legg til Bo" in away
    client.post(
        f"{lisboa}/players/{players['Bo'].id}",
        data={"name": "Bo", "handicap": "9.5"},
    )
    client.post(f"{trip}/players/{players['Bo'].id}")
    back = client.get(trip).get_data(as_text=True)
    assert "Fjern Bo" in back
    assert "9.5" in back
    with app.app_context():
        rejoined = TripPlayer.query.filter_by(player_id=players["Bo"].id).one()
        assert rejoined.handicap == 9.5
        assert db.session.get(Player, players["Bo"].id) is not None

    client.post(f"{lisboa}/players/{players['Ada'].id}/delete")
    with app.app_context():
        assert db.session.get(Player, players["Ada"].id) is None
        assert TripPlayer.query.filter_by(player_id=players["Ada"].id).one_or_none() is None
        assert Trip.query.filter_by(name="Høst 2026").one() is not None
