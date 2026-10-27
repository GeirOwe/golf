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


def test_server_error_page_renders():
    from app import server_error
    with app.test_request_context("/"):
        body, status = server_error(None)
    assert status == 500
    assert "Noe gikk galt" in body


def test_home_asks_for_the_group_link_without_tables():
    response = app.test_client().get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Lenken til gruppen" in body
    assert "Out of bounds" not in body
    assert "<title>Lenken til gruppen</title>" in body
    assert '<a class="brand" href="/">Fore</a>' in body
    assert "Lisboa Høst" not in body
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
