import os
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
