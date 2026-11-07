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

from app import _par_summary, app, db
from course_lookup import SOURCES, _SLOPE_DIRECTORY
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
    assert 'id="hole_count"' in body
    assert "Hent scorekort" in body
    assert "Hent CR/Slope" in body
    assert 'id="rating-picker"' in body
    assert "Ta med valgte" in body
    assert 'id="par-summary"' in body
    assert ">Antall hull<" not in body

    missing = client.post(
        "/baner/ny",
        data={
            "name": "Verify Hills",
            "facility": "Verify Park",
            **_tee_fields(),
        },
    )
    assert missing.status_code == 200
    assert "Hent scorekortet for å sette antall hull." in missing.get_data(as_text=True)

    # Browser-like: prefilled hullnummer 1..9 with blank par/handicap must not error.
    created = client.post(
        "/baner/ny",
        data={
            "name": "Verify Hills",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": [str(n) for n in range(1, 10)],
            "hole_par": [""] * 9,
            "hole_stroke_index": [""] * 9,
            **_tee_fields(),
        },
    )
    assert created.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Hills").one()
        assert course.hole_count == 9
        assert CourseHole.query.filter_by(course_id=course.id).count() == 0
        assert CourseTee.query.filter_by(course_id=course.id).count() == 1
        course_id = course.id
    page = client.get(f"/baner/{course_id}")
    shown = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'name="hole_count"' in shown
    assert "Hent scorekort" in shown
    assert 'name="hole_number"' in shown


def test_new_course_stores_optional_hole_details(tmp_path):
    client = _client(tmp_path)
    numbers = [str(n) for n in range(1, 19)]
    indexes = [str(n) for n in range(1, 19)]
    created = client.post(
        "/baner/ny",
        data={
            "name": "Verify Links",
            "facility": "Verify Bay",
            "hole_count": "18",
            "hole_number": numbers,
            "hole_par": [""] * 18,
            "hole_stroke_index": indexes,
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
        assert holes == {n: (None, n) for n in range(1, 19)}
        course_id = course.id
    page = client.get(f"/baner/{course_id}").get_data(as_text=True)
    assert "Hent scorekort" in page
    assert "<h2>Hull 1–9</h2>" in page
    assert "<h2>Hull 10–18</h2>" in page
    assert 'name="hole_stroke_index"' in page
    assert 'value="18"' in page


def test_par_summary_splits_the_nines_and_names_a_different_tee():
    holes = [{"number": n, "par": 5 if n == 1 else 4} for n in range(1, 19)]
    tees = [
        {"name": "63", "gender": "Herre", "par": 73},
        {"name": "58", "gender": "Dame", "par": 74},
        {"name": "", "gender": "Herre", "par": ""},
    ]
    summary = _par_summary(holes, tees)
    assert summary["ok"] is True
    assert summary["text"] == (
        "Par 1–9 er 37, par 10–18 er 36, totalt 73. "
        "Stemmer med tee-par 73. 58 Dame har par 74."
    )
    assert _par_summary([], tees)["text"] == ""
    assert _par_summary([{"number": 1, "par": ""}], tees)["text"] == ""


def test_hole_par_sum_must_match_tee_par(tmp_path):
    client = _client(tmp_path)
    numbers = [str(n) for n in range(1, 10)]
    pars = ["4"] * 9
    indexes = [""] * 9
    mismatched = client.post(
        "/baner/ny",
        data={
            "name": "Verify Par",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": pars,
            "hole_stroke_index": indexes,
            **_tee_fields(),
        },
    )
    assert mismatched.status_code == 200
    mismatched_body = mismatched.get_data(as_text=True)
    assert (
        "Summen av par på hullene er 36, men ingen tee har det par-tallet (tees: 72)."
        in mismatched_body
    )
    assert "Par 1–9 er 36, totalt 36. Stemmer ikke med tee-par 72." in mismatched_body
    with app.app_context():
        assert GolfCourse.query.filter_by(name="Verify Par").count() == 0

    tee = _tee_fields()
    tee["tee_par"] = ["36", "", "", ""]
    matched = client.post(
        "/baner/ny",
        data={
            "name": "Verify Par",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": pars,
            "hole_stroke_index": indexes,
            **tee,
        },
    )
    assert matched.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Par").one()
        assert course.hole_count == 9
        assert sum(hole.par for hole in course.holes) == 36
        assert course.tees[0].par == 36


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
            "hole_stroke_index": ["", ""],
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
            "hole_stroke_index": [""],
            **_tee_fields(),
        },
    )
    assert "Hull 10 er høyere enn antall hull (9)." in too_high.get_data(as_text=True)


def test_hole_stroke_index_must_be_complete_unique_and_in_range(tmp_path):
    client = _client(tmp_path)
    numbers = [str(n) for n in range(1, 10)]
    blank_pars = [""] * 9

    out_of_range = client.post(
        "/baner/ny",
        data={
            "name": "Verify Index",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": blank_pars,
            "hole_stroke_index": ["1", "2", "3", "4", "5", "6", "7", "8", "10"],
            **_tee_fields(),
        },
    )
    assert (
        "Index for hull 9 må være mellom 1 og 9."
        in out_of_range.get_data(as_text=True)
    )

    duplicate = client.post(
        "/baner/ny",
        data={
            "name": "Verify Index",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": blank_pars,
            "hole_stroke_index": ["1", "2", "3", "4", "5", "6", "7", "8", "8"],
            **_tee_fields(),
        },
    )
    assert "Index 8 er oppgitt mer enn én gang." in duplicate.get_data(as_text=True)

    missing = client.post(
        "/baner/ny",
        data={
            "name": "Verify Index",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers[:8],
            "hole_par": blank_pars[:8],
            "hole_stroke_index": ["1", "2", "3", "4", "5", "6", "7", "8"],
            **_tee_fields(),
        },
    )
    assert (
        "Fyll inn index for alle hull, eller la alle stå tomme."
        in missing.get_data(as_text=True)
    )

    complete = client.post(
        "/baner/ny",
        data={
            "name": "Verify Index",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": blank_pars,
            "hole_stroke_index": ["9", "8", "7", "6", "5", "4", "3", "2", "1"],
            **_tee_fields(),
        },
    )
    assert complete.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Index").one()
        indexes = {
            hole.number: hole.stroke_index
            for hole in CourseHole.query.filter_by(course_id=course.id).all()
        }
        assert indexes == {n: 10 - n for n in range(1, 10)}


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


def test_course_page_can_add_holes_after_create(tmp_path):
    client = _client(tmp_path)
    created = client.post(
        "/baner/ny",
        data={
            "name": "Verify Later",
            "facility": "Verify Park",
            "hole_count": "9",
            **_tee_fields(),
        },
    )
    assert created.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Later").one()
        course_id = course.id
        tee_id = course.tees[0].id

    page = client.get(f"/baner/{course_id}")
    body = page.get_data(as_text=True)
    assert 'name="hole_par"' in body or "hole_par" in body
    assert "readonly" not in body.split('name="hole_count"', 1)[-1][:80]

    tee = {
        "tee_id": [str(tee_id), "", "", ""],
        "tee_name": ["Gul", "", "", ""],
        "tee_gender": ["Herre", "Herre", "Herre", "Herre"],
        "tee_par": ["36", "", "", ""],
        "tee_cr": ["71.2", "", "", ""],
        "tee_slope": ["125", "", "", ""],
    }
    saved = client.post(
        f"/baner/{course_id}",
        data={
            "name": "Verify Later",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": [str(n) for n in range(1, 10)],
            "hole_par": ["4"] * 9,
            "hole_stroke_index": [""] * 9,
            **tee,
        },
    )
    assert saved.status_code == 302
    with app.app_context():
        holes = CourseHole.query.filter_by(course_id=course_id).order_by(CourseHole.number).all()
        assert [hole.par for hole in holes] == [4] * 9


def test_hole_par_sum_allows_differing_tees_and_rechecks_on_tee_edit(tmp_path):
    client = _client(tmp_path)
    numbers = [str(n) for n in range(1, 10)]
    pars = ["4"] * 9
    two_tees = {
        "tee_id": ["", "", "", ""],
        "tee_name": ["Gul", "Rød", "", ""],
        "tee_gender": ["Herre", "Dame", "Herre", "Herre"],
        "tee_par": ["36", "37", "", ""],
        "tee_cr": ["71.2", "73.1", "", ""],
        "tee_slope": ["125", "128", "", ""],
    }
    created = client.post(
        "/baner/ny",
        data={
            "name": "Verify Split",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": pars,
            "hole_stroke_index": [""] * 9,
            **two_tees,
        },
    )
    assert created.status_code == 302
    with app.app_context():
        course = GolfCourse.query.filter_by(name="Verify Split").one()
        course_id = course.id
        tees = {tee.name: tee for tee in course.tees}
        gul_id = tees["Gul"].id
        rod_id = tees["Rød"].id

    ok_edit = client.post(
        f"/baner/{course_id}",
        data={
            "name": "Verify Split",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": pars,
            "hole_stroke_index": [""] * 9,
            "tee_id": [str(gul_id), str(rod_id), "", ""],
            "tee_name": ["Gul", "Rød", "", ""],
            "tee_gender": ["Herre", "Dame", "Herre", "Herre"],
            "tee_par": ["36", "38", "", ""],
            "tee_cr": ["71.2", "73.1", "", ""],
            "tee_slope": ["125", "128", "", ""],
        },
    )
    assert ok_edit.status_code == 302

    drifted = client.post(
        f"/baner/{course_id}",
        data={
            "name": "Verify Split",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": pars,
            "hole_stroke_index": [""] * 9,
            "tee_id": [str(gul_id), str(rod_id), "", ""],
            "tee_name": ["Gul", "Rød", "", ""],
            "tee_gender": ["Herre", "Dame", "Herre", "Herre"],
            "tee_par": ["35", "38", "", ""],
            "tee_cr": ["71.2", "73.1", "", ""],
            "tee_slope": ["125", "128", "", ""],
        },
    )
    assert drifted.status_code == 200
    drifted_body = drifted.get_data(as_text=True)
    assert (
        "Summen av par på hullene er 36, men ingen tee har det par-tallet (tees: 35, 38)."
        in drifted_body
    )
    assert "Stemmer ikke med tee-par 35, 38." in drifted_body
    assert 'value="35"' in drifted_body
    assert 'value="Verify Split"' in drifted_body


def test_invalid_index_keeps_the_rest_of_the_form(tmp_path):
    client = _client(tmp_path)
    numbers = [str(n) for n in range(1, 10)]
    rejected = client.post(
        "/baner/ny",
        data={
            "name": "Verify Keep",
            "facility": "Verify Park",
            "hole_count": "9",
            "hole_number": numbers,
            "hole_par": ["4", "5", "3", "4", "4", "4", "4", "4", "4"],
            "hole_stroke_index": ["1", "2", "3", "4", "5", "6", "7", "8", "10"],
            "hole_meters": ["310", "150", "320", "180", "400", "160", "490", "470", "380"],
            **_tee_fields(),
        },
    )
    body = rejected.get_data(as_text=True)
    assert rejected.status_code == 200
    assert "Index for hull 9 må være mellom 1 og 9." in body
    assert 'value="Verify Keep"' in body
    assert 'value="Verify Park"' in body
    assert 'value="Gul"' in body
    assert 'value="71.2"' in body
    assert 'value="5"' in body
    assert 'value="10"' in body
    assert 'value="310"' in body
    assert body.count('name="hole_par"') == 9
    with app.app_context():
        assert GolfCourse.query.filter_by(name="Verify Keep").count() == 0


def test_fetch_buttons_fill_from_the_club_and_leave_unknown_courses_alone(tmp_path):
    client = _client(tmp_path)
    source = next(item for item in SOURCES if "larvik" in item["aliases"])
    scorecard = """
    <table class="scorecard portrait"><thead>
    <th class="scc-hole">Hull</th><th class="tee-1">63</th>
    <th class="scc-ind">Hcp</th><th class="scc-par">Par</th></thead><tbody>
    <tr><td class="scc-hole">1</td><td class="tee-1">338</td><td class="scc-ind">2</td><td class="scc-par">4</td></tr>
    <tr><td class="scc-hole">2</td><td class="tee-1">152</td><td class="scc-ind">1</td><td class="scc-par">3</td></tr>
    </tbody></table>
    """
    slope_page = '<a class="seltee " rel="seasidebanen" data-send="1">63</a>'
    slope = '<div class="thistee ">63</div><h3>HERRER</h3>Par: 72<br />CR/Slope:<br />73,3/145'
    pages = {
        source["scorecard_url"]: scorecard,
        source["slope_url"]: slope_page,
        source["slope_base"] + "/script/aj_slopetabs?course=seasidebanen&ref=1": slope,
        _SLOPE_DIRECTORY: (
            '<a href="https://slope.no/baner/egersund-golfklubb/">Egersund Golfklubb</a>'
        ),
    }

    def fake_get(url):
        if url not in pages:
            raise AssertionError(url)
        return pages[url]

    app.config["COURSE_HTTP_GET"] = fake_get
    try:
        unknown = client.post(
            "/baner/hent",
            json={"kind": "scorecard", "name": "Quinta da Marinha", "facility": "Cascais"},
        )
        assert unknown.status_code == 200
        assert unknown.json["ok"] is False
        assert "uendret" in unknown.json["error"]
        assert "slope.no" in unknown.json["error"]

        card = client.post(
            "/baner/hent",
            json={"kind": "scorecard", "name": "Larvik - 18 hull", "facility": "Larvik gk"},
        )
        assert card.json["ok"] is True
        assert card.json["holes"] == [
            {"number": 1, "par": 4, "stroke_index": 2, "meters": 338},
            {"number": 2, "par": 3, "stroke_index": 1, "meters": 152},
        ]
        assert card.json["meters_tee"] == "63"
        assert "Larvik Golfklubb" in card.json["message"]

        ratings = client.post(
            "/baner/hent",
            json={"kind": "rating", "name": "Larvik", "facility": ""},
        )
        assert ratings.json["ok"] is True
        assert ratings.json["tees"] == [{
            "name": "63",
            "gender": "Herre",
            "par": 72,
            "course_rating": 73.3,
            "slope_rating": 145,
        }]
    finally:
        app.config.pop("COURSE_HTTP_GET", None)


def test_missing_club_page_falls_back_to_slope_no(tmp_path):
    client = _client(tmp_path)
    directory = (
        '<a href="https://slope.no/baner/egersund-golfklubb/">Egersund Golfklubb</a>'
        '<a href="https://slope.no/baner/preikestolen-golfklubb/">Preikestolen Golfklubb</a>'
    )
    card = """
    <div class="ghs-sc-card" data-tee-id="1">
      <span class="ghs-sc-teename">Herrer, tee Gul</span>
      <table class="ghs-sc-table"><thead><tr>
        <th>Hull</th><th>1</th><th>2</th>
      </tr></thead><tbody>
        <tr class="ghs-sc-par"><th>Par</th><td>4</td><td>3</td><td class="ghs-sc-sum">7</td></tr>
        <tr class="ghs-sc-index"><th>Indeks</th><td>2</td><td>1</td><td class="ghs-sc-sum"></td></tr>
        <tr class="ghs-sc-length"><th>Lengde</th><td>260</td><td>117</td><td class="ghs-sc-sum">377</td></tr>
      </tbody></table>
    </div>
    <div class="ghs-sc-card" data-tee-id="2">
      <span class="ghs-sc-teename">Herrer, tee Hvit</span>
      <table class="ghs-sc-table"><thead><tr>
        <th>Hull</th><th>1</th><th>2</th>
      </tr></thead><tbody>
        <tr class="ghs-sc-par"><th>Par</th><td>4</td><td>3</td><td class="ghs-sc-sum">7</td></tr>
        <tr class="ghs-sc-index"><th>Indeks</th><td>2</td><td>1</td><td class="ghs-sc-sum"></td></tr>
        <tr class="ghs-sc-length"><th>Lengde</th><td>275</td><td>142</td><td class="ghs-sc-sum">417</td></tr>
      </tbody></table>
    </div>
    """
    ratings = """
    <select id="teeSelector">
      <optgroup label="Menn">
        <option data-slope="136" data-course="68.4" data-par="70">Hvit</option>
        <option data-slope="124" data-course="65.7" data-par="70">Rød</option>
      </optgroup>
      <optgroup label="Damer">
        <option data-slope="142" data-course="73.9" data-par="70">Hvit</option>
      </optgroup>
    </select>
    """
    pages = {
        _SLOPE_DIRECTORY: directory,
        "https://slope.no/baner/egersund-golfklubb/": card + ratings,
    }

    def fake_get(url):
        if url not in pages:
            raise AssertionError(url)
        return pages[url]

    app.config["COURSE_HTTP_GET"] = fake_get
    try:
        ambiguous = client.post(
            "/baner/hent",
            json={"kind": "scorecard", "name": "Golf", "facility": ""},
        )
        assert ambiguous.json["ok"] is False

        fetched = client.post(
            "/baner/hent",
            json={"kind": "scorecard", "name": "Egersund", "facility": "Egersund Golfklubb"},
        )
        assert fetched.json["ok"] is True
        assert fetched.json["meters_tee"] == "Hvit"
        assert fetched.json["holes"][0]["meters"] == 275
        assert "slope.no" in fetched.json["message"]
        assert "rett det som ikke stemmer" in fetched.json["message"]

        slope = client.post(
            "/baner/hent",
            json={"kind": "rating", "name": "Egersund", "facility": ""},
        )
        assert slope.json["ok"] is True
        assert slope.json["tees"] == [
            {"name": "Hvit", "gender": "Herre", "par": 70, "course_rating": 68.4, "slope_rating": 136},
            {"name": "Rød", "gender": "Herre", "par": 70, "course_rating": 65.7, "slope_rating": 124},
            {"name": "Hvit", "gender": "Dame", "par": 70, "course_rating": 73.9, "slope_rating": 142},
        ]
    finally:
        app.config.pop("COURSE_HTTP_GET", None)


def test_missing_meters_column_is_added(tmp_path):
    client = _client(tmp_path)
    client.get("/baner")
    with app.app_context():
        db.session.execute(text("ALTER TABLE course_holes DROP COLUMN meters"))
        db.session.commit()
        app._schema_ready = False
    client.get("/baner")
    with app.app_context():
        columns = {
            column["name"]
            for column in inspect(db.session.get_bind()).get_columns("course_holes")
        }
    assert "meters" in columns
