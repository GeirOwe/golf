"""
Golf Course API client (https://api.golfcourseapi.com/docs/api/)
"""

import os
from typing import Any

import requests

API_BASE = "https://api.golfcourseapi.com"
DEFAULT_SEARCH = "stavanger golfklubb"

# Extra search terms per country (API has no /countries endpoint – we search and filter)
COUNTRY_SEARCH_TERMS: dict[str, list[str]] = {
    "norway": ["norway", "norge", "oslo", "bergen", "stavanger", "trondheim"],
    "norge": ["norway", "norge", "oslo", "bergen", "stavanger", "trondheim"],
    "united states": ["united states", "usa", "golf club"],
    "usa": ["united states", "usa", "golf club"],
    "portugal": ["portugal", "lisbon", "lisboa", "porto"],
    "spain": ["spain", "madrid", "barcelona"],
    "sweden": ["sweden", "sverige", "stockholm"],
    "denmark": ["denmark", "copenhagen"],
    "germany": ["germany", "deutschland", "berlin"],
    "united kingdom": ["united kingdom", "england", "scotland", "uk golf"],
}


def _normalize_country_key(country: str) -> str:
    return country.strip().lower()


def _country_aliases(country: str) -> set[str]:
    key = _normalize_country_key(country)
    aliases = {key}
    mapping = {
        "norway": {"norway", "norge"},
        "norge": {"norway", "norge"},
        "usa": {"united states", "usa", "us", "u.s.", "u.s.a."},
        "us": {"united states", "usa", "us", "u.s.", "u.s.a."},
        "united states": {"united states", "usa", "us", "u.s.", "u.s.a."},
        "uk": {"united kingdom", "uk", "great britain"},
        "united kingdom": {"united kingdom", "uk", "great britain"},
    }
    aliases.update(mapping.get(key, set()))
    return aliases


def _location_country_matches(location_country: str | None, country: str) -> bool:
    if not location_country:
        return False
    loc = location_country.strip().lower()
    return loc in _country_aliases(country)


def search_courses(query: str) -> list[dict[str, Any]]:
    """Raw search – returns course list from API."""
    data = _get("/v1/search", {"search_query": query})
    return data.get("courses") or []


def list_courses_by_country(country: str, max_queries: int = 5) -> list[dict[str, Any]]:
    """
    List courses with id for a country by running several searches and filtering
    on location.country. API has no dedicated country listing endpoint.
    """
    country = country.strip()
    if not country:
        raise GolfCourseAPIError("Angi et land (f.eks. Norway, Portugal, United States).")

    key = _normalize_country_key(country)
    terms = COUNTRY_SEARCH_TERMS.get(key, [country])
    if country.lower() not in [t.lower() for t in terms]:
        terms = [country] + terms
    terms = terms[:max_queries]

    by_id: dict[int, dict[str, Any]] = {}
    for term in terms:
        for course in search_courses(term):
            loc = course.get("location") or {}
            if not _location_country_matches(loc.get("country"), country):
                continue
            cid = course.get("id")
            if cid is None:
                continue
            by_id[cid] = {
                "id": cid,
                "club_name": course.get("club_name") or "",
                "course_name": course.get("course_name") or "",
                "city": loc.get("city") or "",
                "state": loc.get("state") or "",
                "country": loc.get("country") or "",
            }

    rows = sorted(by_id.values(), key=lambda r: (r["club_name"].lower(), r["course_name"].lower()))
    return rows


class GolfCourseAPIError(Exception):
    """Raised when the Golf Course API request fails."""


def _headers() -> dict[str, str]:
    api_key = os.getenv("GOLFCOURSE_API_KEY")
    if not api_key:
        raise GolfCourseAPIError(
            "Mangler GOLFCOURSE_API_KEY. Legg nøkkelen i .env (lokalt) eller Render Environment."
        )
    return {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    headers = _headers()
    headers["Cache-Control"] = "no-cache"
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
    except requests.RequestException as exc:
        raise GolfCourseAPIError(f"Nettverksfeil mot Golf Course API: {exc}") from exc

    if response.status_code == 401:
        raise GolfCourseAPIError("API-nøkkel mangler eller er ugyldig.")
    if response.status_code == 304:
        raise GolfCourseAPIError(
            "API returnerte 304 (cache) uten data. Prøv igjen om litt."
        )
    if response.status_code == 429:
        raise GolfCourseAPIError(
            "API rate limit nådd (gratis plan: ca. 50 kall/dag). Prøv igjen senere."
        )
    if response.status_code != 200:
        raise GolfCourseAPIError(
            f"API-feil ({response.status_code}): {response.text[:200]}"
        )
    if not response.text.strip():
        raise GolfCourseAPIError("API returnerte tomt svar.")
    return response.json()


def _pick_course_id(courses: list[dict[str, Any]], query: str) -> int | None:
    if not courses:
        return None
    q = query.lower()
    for course in courses:
        club = (course.get("club_name") or "").lower()
        name = (course.get("course_name") or "").lower()
        if "stavanger" in club or "stavanger" in name:
            return course["id"]
    return courses[0]["id"]


def _unwrap_course(payload: dict[str, Any]) -> dict[str, Any]:
    """API returns { \"course\": { ... } } on GET /v1/courses/{id}."""
    if "course" in payload and isinstance(payload["course"], dict):
        return payload["course"]
    return payload


def _tee_rows(tees_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not tees_data:
        return []
    rows = []
    for gender in ("male", "female"):
        for tee in tees_data.get(gender) or []:
            rows.append({
                "gender": "Herre" if gender == "male" else "Dame",
                "tee_name": tee.get("tee_name", "-"),
                "course_rating": tee.get("course_rating"),
                "slope_rating": tee.get("slope_rating"),
                "par_total": tee.get("par_total"),
            })
    return rows


def lookup_course_ratings(
    search_query: str = DEFAULT_SEARCH,
    course_id: int | None = None,
) -> dict[str, Any]:
    """
    Search for a course and return club name plus CR/slope per tee.
    Pass course_id to skip search. Env GOLFCOURSE_COURSE_ID also skips search.
    """
    if course_id is not None:
        return fetch_course_by_id(course_id)

    course_id_env = os.getenv("GOLFCOURSE_COURSE_ID", "").strip()
    if course_id_env.isdigit():
        course_id = int(course_id_env)
    else:
        search = _get("/v1/search", {"search_query": search_query})
        courses = search.get("courses") or []
        course_id = _pick_course_id(courses, search_query)
        if course_id is None:
            raise GolfCourseAPIError(
                f"Ingen bane funnet for «{search_query}» i Golf Course API. "
                "Stavanger GK ligger ofte ikke i databasen (begrenset Norge-dekning). "
                "Søk på golfcourseapi.com etter banen, sett GOLFCOURSE_COURSE_ID i .env, "
                "eller prøv et annet søkeord i feltet under."
            )

    return fetch_course_by_id(course_id)


def fetch_course_by_id(course_id: int) -> dict[str, Any]:
    """Load one course by numeric id (as in golfcourseapi.com docs)."""
    raw = _get(f"/v1/courses/{course_id}")
    details = _unwrap_course(raw)
    return {
        "course_id": details.get("id", course_id),
        "club_name": details.get("club_name"),
        "course_name": details.get("course_name"),
        "location": details.get("location") or {},
        "tees": _tee_rows(details.get("tees")),
    }
