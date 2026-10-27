import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-shell-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db


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


def test_token_lookup_hides_the_other_group(tmp_path):
    client = _client(tmp_path)
    opened = client.post("/start", data={"secret": "verify-secret"})
    assert opened.status_code == 200
    assert "Fjord" not in opened.get_data(as_text=True)

    first = client.post("/start/groups", data={"name": "Fjord"})
    second = client.post("/start/groups", data={"name": "Algarve"})
    assert first.status_code == 302
    assert first.headers["Location"] == "/g/fjord"
    assert second.headers["Location"] == "/g/algarve"

    fjord = client.get(first.headers["Location"])
    algarve = client.get(second.headers["Location"])
    fjord_body = fjord.get_data(as_text=True)
    algarve_body = algarve.get_data(as_text=True)
    assert fjord.status_code == 200
    assert "<title>Fjord</title>" in fjord_body
    assert '<a class="brand" href="/">Fjord</a>' in fjord_body
    assert "<p>Golf - et Owen Labs produkt</p>" in fjord_body
    assert "Algarve" not in fjord_body
    assert "Ingen turer ennå." in fjord_body
    assert "Lisboa Høst" not in fjord_body
    assert algarve.status_code == 200
    assert "<title>Algarve</title>" in algarve_body
    assert '<a class="brand" href="/">Algarve</a>' in algarve_body
    assert "Fjord" not in algarve_body
    assert "Lisboa Høst" not in algarve_body

    missing = client.get("/g/not-a-real-token")
    missing_body = missing.get_data(as_text=True)
    assert missing.status_code == 404
    assert "Fjord" not in missing_body
    assert "Algarve" not in missing_body


def test_wrong_secret_hides_group_names(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    client.post("/start/groups", data={"name": "Fjord"})

    other = app.test_client()
    missed = other.post("/start", data={"secret": "wrong-secret"})
    missed_body = missed.get_data(as_text=True)
    assert missed.status_code == 200
    assert "Fjord" not in missed_body
    assert "Lisboa Høst" not in missed_body
    assert '<a class="brand" href="/">Fore</a>' in missed_body
    assert "Feil kode." in missed_body

    kept = client.get("/start")
    assert "Fjord" in kept.get_data(as_text=True)

    blocked = other.post("/start/groups", data={"name": "Algarve"})
    assert "Algarve" not in blocked.get_data(as_text=True)
    assert "Algarve" not in client.get("/start").get_data(as_text=True)


def test_home_asks_for_the_group_link(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    client.post("/start/groups", data={"name": "Fjord"})
    home = client.get("/")
    body = home.get_data(as_text=True)
    assert home.status_code == 200
    assert "Lenken til gruppen" in body
    assert "Out of bounds" not in body
    assert "<title>Lenken til gruppen</title>" in body
    assert "Fjord" not in body
    assert "Lisboa Høst" not in body


def test_rename_keeps_the_link_and_the_other_group(tmp_path):
    client = _client(tmp_path)
    client.post("/start", data={"secret": "verify-secret"})
    created = client.post("/start/groups", data={"name": "Fjord"})
    path = created.headers["Location"]
    algarve = client.post("/start/groups", data={"name": "Algarve"}).headers["Location"]

    form = client.get(path + "/navn")
    form_body = form.get_data(as_text=True)
    assert form.status_code == 200
    assert "<h1>Endre navn</h1>" in form_body
    assert 'value="Fjord"' in form_body

    blank = client.post(path + "/navn", data={"name": "   "})
    assert "Skriv et gruppenavn." in blank.get_data(as_text=True)
    assert "<title>Fjord</title>" in client.get(path).get_data(as_text=True)

    renamed = client.post(path + "/navn", data={"name": "  Kyst  "})
    assert renamed.status_code == 302
    assert renamed.headers["Location"] == "/g/kyst"
    assert client.get(path).status_code == 404
    body = client.get("/g/kyst").get_data(as_text=True)
    assert "<title>Kyst</title>" in body
    assert '<a class="brand" href="/">Kyst</a>' in body
    assert "Fjord" not in body
    start = client.get("/start").get_data(as_text=True)
    assert "Kyst" in start
    assert "Fjord" not in start
    assert "Kyst" not in client.get(algarve).get_data(as_text=True)
    assert client.get("/g/not-a-real-token/navn").status_code == 404
    with app.app_context():
        from database import Group
        token = Group.query.filter_by(name="Kyst").one().token
    kept = client.get("/g/" + token)
    assert kept.status_code == 200
    assert "<title>Kyst</title>" in kept.get_data(as_text=True)


def test_removed_routes_are_gone(tmp_path):
    client = _client(tmp_path)
    for path in ("/players", "/ai-story", "/flights", "/finale", "/admin"):
        assert client.get(path).status_code == 404
