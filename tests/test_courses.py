import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_SKIP_DOTENV"] = "1"
os.environ["ORGANIZER_SECRET"] = "verify-secret"
os.environ["FLASK_SECRET_KEY"] = "verify-flask-secret"
_DB_PATH = Path(tempfile.mkdtemp(prefix="golf-courses-")) / "golf.db"
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.resolve().as_posix()

from app import app, db
from database import CourseHole, CourseTee, GolfCourse


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


def _tee_fields():
    return {
        "tee_id": ["", "", "", ""],
        "tee_name": ["Gul", "", "", ""],
        "tee_gender": ["Herre", "Herre", "Herre", "Herre"],
        "tee_par": ["72", "", "", ""],
        "tee_cr": ["71.2", "", "", ""],
        "tee_slope": ["125", "", "", ""],
    }


def test_new_course_requires_hole_count_and_allows_skipping_hole_details(tmp_path):
    client = _client(tmp_path)
    form = client.get("/baner/ny")
    body = form.get_data(as_text=True)
    assert form.status_code == 200
    assert 'name="hole_count"' in body
    assert "Hull (valgfritt)" in body

    missing = client.post(
        "/baner/ny",
        data={
            "name": "Verify Hills",
            "facility": "Verify Park",
            **_tee_fields(),
        },
    )
    assert missing.status_code == 200
    assert "Skriv antall hull." in missing.get_data(as_text=True)

    created = client.post(
        "/baner/ny",
        data={
            "name": "Verify Hills",
            "facility": "Verify Park",
            "hole_count": "18",
            **_tee_fields(),
        },
    )
    assert created.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Hills").one()
        assert course.hole_count == 18
        assert CourseHole.query.filter_by(course_id=course.id).count() == 0
        assert CourseTee.query.filter_by(course_id=course.id).count() == 1
        course_id = course.id
    page = client.get(f"/baner/{course_id}")
    shown = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'value="18"' in shown
    assert "<h2>Hull</h2>" not in shown


def test_new_course_stores_optional_hole_details(tmp_path):
    client = _client(tmp_path)
    created = client.post(
        "/baner/ny",
        data={
            "name": "Verify Links",
            "facility": "Verify Bay",
            "hole_count": "18",
            "hole_number": ["1", "2", "9", "10", "18"],
            "hole_par": ["4", "3", "5", "4", "5"],
            "hole_stroke_index": ["7", "", "1", "2", "3"],
            **_tee_fields(),
        },
    )
    assert created.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Links").one()
        assert course.hole_count == 18
        holes = {
            hole.number: (hole.par, hole.stroke_index)
            for hole in CourseHole.query.filter_by(course_id=course.id).all()
        }
        assert holes == {
            1: (4, 7),
            2: (3, None),
            9: (5, 1),
            10: (4, 2),
            18: (5, 3),
        }
        course_id = course.id
    page = client.get(f"/baner/{course_id}").get_data(as_text=True)
    assert "<h2>Hull</h2>" in page
    assert "<h3>Hull 1–9</h3>" in page
    assert "<h3>Hull 10–18</h3>" in page
    front, back = page.split("<h3>Hull 10–18</h3>", 1)
    assert ">1<" in front and ">9<" in front
    assert ">10<" not in front
    assert ">10<" in back and ">18<" in back
    assert ">1<" not in back.split("<tbody>", 1)[-1]


def test_new_course_rejects_invalid_optional_holes(tmp_path):
    client = _client(tmp_path)
    duplicate = client.post(
        "/baner/ny",
        data={
            "name": "Verify Dunes",
            "facility": "Verify Coast",
            "hole_count": "9",
            "hole_number": ["1", "1"],
            "hole_par": ["4", "5"],
            "hole_stroke_index": ["1", "2"],
            **_tee_fields(),
        },
    )
    assert "Hull 1 er oppgitt mer enn én gang." in duplicate.get_data(as_text=True)

    too_high = client.post(
        "/baner/ny",
        data={
            "name": "Verify Dunes",
            "facility": "Verify Coast",
            "hole_count": "9",
            "hole_number": ["10"],
            "hole_par": ["4"],
            "hole_stroke_index": ["1"],
            **_tee_fields(),
        },
    )
    assert "Hull 10 er høyere enn antall hull (9)." in too_high.get_data(as_text=True)


def test_missing_hole_count_column_is_added(tmp_path):
    client = _client(tmp_path)
    client.get("/baner")
    with app.app_context():
        db.session.execute(text("ALTER TABLE golf_courses DROP COLUMN hole_count"))
        db.session.commit()
        app._schema_ready = False
    client.get("/baner")
    with app.app_context():
        columns = {
            column["name"]
            for column in inspect(db.session.get_bind()).get_columns("golf_courses")
        }
    assert "hole_count" in columns
