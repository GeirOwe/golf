import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-cutover-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db

_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("cutover", _REPO / "scripts" / "cutover.py")
cutover = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cutover)


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


def _seed(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE golf_courses (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            facility VARCHAR(120) NOT NULL,
            created_at DATETIME
        );
        CREATE TABLE course_tees (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            name VARCHAR(50) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            par INTEGER NOT NULL,
            course_rating FLOAT NOT NULL,
            slope_rating INTEGER NOT NULL,
            created_at DATETIME
        );
        CREATE TABLE players (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            handicap FLOAT
        );
        CREATE TABLE rounds (id INTEGER PRIMARY KEY);
        CREATE TABLE round_scores (id INTEGER PRIMARY KEY, score INTEGER);
        CREATE TABLE finale_scores (
            id INTEGER PRIMARY KEY,
            score INTEGER,
            bonus INTEGER
        );
        INSERT INTO golf_courses (name, facility) VALUES
            ('Verify Hills', 'Lisboa'),
            ('Penina', 'Algarve');
        INSERT INTO course_tees (
            course_id, name, gender, par, course_rating, slope_rating
        ) VALUES
            (1, 'Blå', 'Herre', 72, 71.2, 125),
            (1, 'Rød', 'Dame', 72, 73.1, 128),
            (2, 'Hvit', 'Herre', 71, 70.4, 130);
        INSERT INTO players (name, handicap) VALUES ('Gammel Ada', 12.4);
        INSERT INTO finale_scores (score, bonus) VALUES (30, 4);
        """
    )
    connection.commit()
    connection.close()


def _counts(path):
    connection = sqlite3.connect(path)
    try:
        courses = connection.execute("SELECT count(*) FROM golf_courses").fetchone()[0]
        tees = connection.execute("SELECT count(*) FROM course_tees").fetchone()[0]
        players = [row[0] for row in connection.execute("SELECT name FROM players")]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()
    return courses, tees, players, tables


def _run_script(path, database_url=None):
    env = os.environ.copy()
    env["FLASK_SKIP_DOTENV"] = "1"
    if database_url is None:
        env.pop("DATABASE_URL", None)
    else:
        env["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "cutover.py")],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
    )


def test_script_refuses_a_missing_database_url():
    completed = _run_script(None, database_url="")
    assert completed.returncode == 1
    assert "DATABASE_URL is missing" in completed.stderr


def test_script_keeps_courses_and_drops_the_old_player(tmp_path):
    path = tmp_path / "golf.db"
    _seed(path)
    url = "sqlite:///" + path.resolve().as_posix()
    completed = _run_script(path, database_url=url)
    assert completed.returncode == 0, completed.stderr
    assert "golf_courses=2" in completed.stdout
    assert "course_tees=3" in completed.stdout
    assert "sqlite" not in completed.stdout
    courses, tees, players, tables = _counts(path)
    assert courses == 2
    assert tees == 3
    assert players == []
    assert "finale_scores" not in tables
    assert "Gammel Ada" not in players

    _use_database(path)
    page = app.test_client().get("/baner")
    body = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Verify Hills" in body
    assert "Penina" in body
    assert "Gammel Ada" not in body


def test_script_rolls_back_when_a_course_count_changes(tmp_path, monkeypatch):
    path = tmp_path / "golf.db"
    _seed(path)
    url = "sqlite:///" + path.resolve().as_posix()

    original = cutover.create_schema

    def sabotage(connection):
        original(connection)
        connection.execute(text(
            "DELETE FROM course_tees WHERE course_id = ("
            "SELECT MIN(id) FROM golf_courses)"
        ))
        connection.execute(text(
            "DELETE FROM golf_courses WHERE id = ("
            "SELECT MIN(id) FROM golf_courses)"
        ))

    monkeypatch.setattr(cutover, "create_schema", sabotage)
    assert cutover.run(url) == 2
    courses, tees, players, tables = _counts(path)
    assert courses == 2
    assert tees == 3
    assert players == ["Gammel Ada"]
    assert "finale_scores" in tables


def test_gate_lists_no_group_names_and_opens_the_link(tmp_path):
    _use_database(tmp_path / "golf.db")
    client = app.test_client()
    client.post("/start", data={"secret": "verify-secret"})
    opened = client.post("/start/groups", data={"name": "Lisboa"})
    token_path = opened.headers["Location"]
    home = client.get("/")
    body = home.get_data(as_text=True)
    assert home.status_code == 200
    assert "Lenken til gruppen" in body
    assert "Out of bounds" not in body
    assert "Lisboa" not in body

    pasted = "https://example.com" + token_path + "/trips/1"
    followed = client.post("/", data={"link": pasted})
    assert followed.status_code == 302
    assert followed.headers["Location"].endswith(token_path + "/trips/1")
    assert "example.com" not in followed.headers["Location"]

    rejected = client.post("/", data={"link": "https://example.com/start"})
    assert rejected.status_code == 200
    assert "Lim inn lenken til gruppen." in rejected.get_data(as_text=True)
