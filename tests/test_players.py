import os
import re
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-players-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db
from database import Group, Player
from models import HandicapError


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


def test_handicap_limit_and_group_query(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    _open_group(client, "Fjord")
    _open_group(client, "Algarve")

    with app.app_context():
        fjord = Group.query.filter_by(name="Fjord").one()
        algarve = Group.query.filter_by(name="Algarve").one()
        with pytest.raises(HandicapError):
            Player(name="Ada", handicap=54.1, group_id=fjord.id)
        ada = Player(name="Ada", handicap=54.0, group_id=fjord.id)
        bo = Player(name="Bo", handicap=10.0, group_id=algarve.id)
        db.session.add_all([ada, bo])
        db.session.commit()
        stored = Player.query.filter_by(group_id=fjord.id).all()
        others = Player.query.filter_by(group_id=algarve.id).all()

    assert [player.name for player in stored] == ["Ada"]
    assert stored[0].handicap == 54.0
    assert [player.name for player in others] == ["Bo"]
    assert ada.id not in {player.id for player in others}


def _chrome(body, name):
    assert f"<title>{name}</title>" in body
    assert f'<a class="brand" href="/">{name}</a>' in body
    assert f"<p>{name}</p>" in body
    assert "<title>Fore</title>" not in body
    assert '<a class="brand" href="/">Fore</a>' not in body


def _edit_path(client, group_path, name):
    body = client.get(group_path).get_data(as_text=True)
    for href in re.findall(r'href="([^"]+/players/\d+)"', body):
        page = client.get(href).get_data(as_text=True)
        if f'value="{name}"' in page:
            return href
    raise AssertionError(name)


def test_player_pages_stay_on_the_group(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    lisboa = _open_group(client, "Lisboa")
    algarve = _open_group(client, "Algarve")

    empty = client.get(lisboa)
    empty_body = empty.get_data(as_text=True)
    assert empty.status_code == 200
    _chrome(empty_body, "Lisboa")
    assert empty_body.count('class="empty"') == 1
    assert "Ingen turer ennå." in empty_body
    assert "Ada" not in empty_body

    form = client.get(lisboa + "/players")
    assert form.status_code == 200
    _chrome(form.get_data(as_text=True), "Lisboa")

    created = client.post(
        lisboa + "/players",
        data={"name": "Ada", "handicap": "12.4"},
        follow_redirects=True,
    )
    created_body = created.get_data(as_text=True)
    assert created.status_code == 200
    assert "Ada" in created_body
    assert "12.4" in created_body
    _chrome(created_body, "Lisboa")
    assert "Ada" not in client.get(algarve).get_data(as_text=True)

    rejected = client.post(
        lisboa + "/players",
        data={"name": "Nia", "handicap": "54.1"},
    )
    rejected_body = rejected.get_data(as_text=True)
    assert rejected.status_code == 200
    assert '<span class="entity-row__name">Ada</span>' in rejected_body
    assert "12.4" in rejected_body
    assert '<span class="entity-row__name">Nia</span>' not in rejected_body
    assert "Handicap kan ikke være høyere enn 54.0." in rejected_body

    blank = client.post(
        lisboa + "/players",
        data={"name": "   ", "handicap": "10"},
    )
    blank_body = blank.get_data(as_text=True)
    assert "Skriv et navn." in blank_body
    assert "Nia" not in blank_body

    capped = client.post(
        lisboa + "/players",
        data={"name": "Cato", "handicap": "54,0"},
        follow_redirects=True,
    )
    capped_body = capped.get_data(as_text=True)
    assert "Cato" in capped_body
    assert "54.0" in capped_body

    ada_path = _edit_path(client, lisboa, "Ada")
    edit_page = client.get(ada_path)
    _chrome(edit_page.get_data(as_text=True), "Lisboa")
    edited = client.post(
        ada_path,
        data={"name": "Ada", "handicap": "18.2"},
        follow_redirects=True,
    )
    edited_body = edited.get_data(as_text=True)
    assert "18.2" in edited_body
    assert "12.4" not in edited_body

    kept = client.post(ada_path, data={"name": "Ada", "handicap": "54.1"})
    assert "Handicap kan ikke være høyere enn 54.0." in kept.get_data(as_text=True)
    assert "18.2" in client.get(lisboa).get_data(as_text=True)

    client.post(
        lisboa + "/players",
        data={"name": "Bo", "handicap": "8"},
        follow_redirects=True,
    )
    bo_path = _edit_path(client, lisboa, "Bo")
    removed = client.post(bo_path + "/delete", follow_redirects=True)
    removed_body = removed.get_data(as_text=True)
    assert "Ada" in removed_body
    assert "Bo" not in removed_body
    assert "Cato" in removed_body

    ada_id = ada_path.rsplit("/", 1)[-1]
    assert client.get(f"{algarve}/players/{ada_id}").status_code == 404
    assert client.post(
        f"{algarve}/players/{ada_id}",
        data={"name": "Ada", "handicap": "1"},
    ).status_code == 404
    assert client.post(f"{algarve}/players/{ada_id}/delete").status_code == 404
    algarve_body = client.get(algarve).get_data(as_text=True)
    assert "Ada" not in algarve_body
    assert "Cato" not in algarve_body
    assert algarve_body.count('class="empty"') == 1

    home = client.get("/")
    home_body = home.get_data(as_text=True)
    assert "Fore. Out of bounds." in home_body
    assert "<title>Fore</title>" in home_body
    assert "Ada" not in home_body
    assert "Lisboa" not in home_body
