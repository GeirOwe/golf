import os
import sqlite3
import tempfile
from pathlib import Path

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-hold-")) / "golf.db"
_DB_PATH.touch()
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app


def test_home_renders_holding_page_without_tables():
    response = app.test_client().get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Fore. Out of bounds." in body
    assert "En omskriving pågår." in body
    if _DB_PATH.stat().st_size == 0:
        return
    connection = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()
    assert names == set()
