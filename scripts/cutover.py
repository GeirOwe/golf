"""Keep the courses and replace the old player tables.

Reads DATABASE_URL. Refuses to run when it is missing. Records the
golf_courses and course_tees counts, drops players, rounds, round_scores,
and finale_scores when those tables exist, then creates the new tables.
If either course count changes, the transaction rolls back and the process
exits 2.
"""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import create_engine, event, text  # noqa: E402

from database import db  # noqa: E402

_OLD_TABLES = ("finale_scores", "round_scores", "rounds", "players")


def _database_url():
    url = os.environ.get("DATABASE_URL") or ""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _engine(database_url):
    engine = create_engine(database_url)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _connect(dbapi_connection, _record):
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def _begin(connection):
            connection.exec_driver_sql("BEGIN")
    return engine


def _counts(connection):
    courses = connection.execute(text("SELECT count(*) FROM golf_courses")).scalar()
    tees = connection.execute(text("SELECT count(*) FROM course_tees")).scalar()
    return int(courses), int(tees)


def _table_names(connection):
    if connection.dialect.name == "sqlite":
        rows = connection.execute(text(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ))
        return {row[0] for row in rows}
    rows = connection.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ))
    return {row[0] for row in rows}


def _already_applied(connection):
    tables = _table_names(connection)
    if "trips" in tables or "trip_players" in tables:
        return True
    if "players" not in tables:
        return False
    if connection.dialect.name == "sqlite":
        rows = connection.execute(text("PRAGMA table_info(players)"))
        return any(row[1] == "group_id" for row in rows)
    rows = connection.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'players' AND column_name = 'group_id'"
    ))
    return rows.first() is not None


def drop_old_tables(connection):
    for name in _OLD_TABLES:
        connection.execute(text(f"DROP TABLE IF EXISTS {name}"))


def create_schema(connection):
    db.metadata.create_all(bind=connection)


def run(database_url):
    engine = _engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        if _already_applied(connection):
            print("cutover already applied", file=sys.stderr)
            transaction.rollback()
            return 1
        before = _counts(connection)
        drop_old_tables(connection)
        create_schema(connection)
        after = _counts(connection)
        if after != before:
            transaction.rollback()
            return 2
        transaction.commit()
        print(f"golf_courses={after[0]}")
        print(f"course_tees={after[1]}")
        return 0
    except Exception:
        transaction.rollback()
        raise
    finally:
        connection.close()
        engine.dispose()


def main():
    database_url = _database_url()
    if not database_url:
        print("DATABASE_URL is missing", file=sys.stderr)
        return 1
    try:
        return run(database_url)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
