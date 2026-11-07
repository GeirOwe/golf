"""Fetch scorecard and tee ratings from a club's own published pages.

Only hosts listed below are contacted. A page that cannot be parsed is
rejected, so the form is never filled with guessed numbers.
"""

import html
import re
import unicodedata
from urllib.parse import urlencode, urlparse

import requests


class LookupError(Exception):
    """The club page could not be used. The message is safe to show."""


# Club sites that publish the same scorecard and slope markup.
# Aliases are matched as whole words against the course name and facility.
SOURCES = (
    {
        "aliases": ("larvik",),
        "label": "Larvik Golfklubb",
        "hosts": ("larvikgolf.no",),
        "scorecard_url": "https://larvikgolf.no/banene/scorekort/seasidebanen",
        "slope_url": "https://larvikgolf.no/banene/slopetabeller",
        "slope_base": "https://larvikgolf.no",
    },
    {
        "aliases": ("bjaavann",),
        "label": "Bjaavann golfklubb",
        "hosts": ("bjaavanngk.no",),
        "scorecard_url": "https://bjaavanngk.no/banen/scorekort",
        "slope_url": "https://bjaavanngk.no/banen/slopetabeller",
        "slope_base": "https://bjaavanngk.no",
    },
)

_CELL = re.compile(r"<t([dh])([^>]*)>(.*?)</t\1>", re.I | re.S)
_CLASS = re.compile(r'class="([^"]*)"', re.I)
_TAG = re.compile(r"<[^>]+>")
_TABLE = re.compile(r'<table class="scorecard[^"]*">(.*?)</table>', re.I | re.S)
_SELTEE = re.compile(r"<a\b[^>]*class=\"[^\"]*\bseltee\b[^\"]*\"[^>]*>.*?</a>", re.I | re.S)
_ATTR = re.compile(r'(\w[\w-]*)="([^"]*)"')
_GENDER = {"herre": "Herre", "herrer": "Herre", "dame": "Dame", "damer": "Dame"}
_MAX_BYTES = 1_500_000


def fetch_scorecard(name, facility, http_get=None):
    """Return par, stroke index and meters, or a reason the form was left as it was."""
    try:
        return _fetch_scorecard(name, facility, http_get)
    except LookupError as exc:
        return {"ok": False, "error": str(exc)}


def fetch_ratings(name, facility, http_get=None):
    """Return tee par, course rating and slope, or a reason the form was left as it was."""
    try:
        return _fetch_ratings(name, facility, http_get)
    except LookupError as exc:
        return {"ok": False, "error": str(exc)}


def _fetch_scorecard(name, facility, http_get):
    source = _source_for(name, facility)
    page = _get(source["scorecard_url"], source["hosts"], http_get)
    card = _choose_scorecard(page, f"{name} {facility}")
    if card is None:
        raise LookupError(
            f"Scorekortet fra {source['label']} kunne ikke leses. Skjemaet er uendret."
        )
    return {
        "ok": True,
        "source": source["label"],
        "url": source["scorecard_url"],
        "meters_tee": card["meters_tee"],
        "hole_count": len(card["holes"]),
        "holes": card["holes"],
        "message": (
            f"Scorekort fra {source['label']}. "
            f"Meter er fra utslag {card['meters_tee']}."
        ),
    }


def _fetch_ratings(name, facility, http_get):
    source = _source_for(name, facility)
    page = _get(source["slope_url"], source["hosts"], http_get)
    listed = _slope_tee_links(page)
    if not listed:
        raise LookupError(
            f"Slopetabellen fra {source['label']} kunne ikke leses. Skjemaet er uendret."
        )
    tees = []
    seen = set()
    for link in listed[:12]:
        url = source["slope_base"] + "/script/aj_slopetabs?" + urlencode(
            {"course": link["course"], "ref": link["ref"]}
        )
        fragment = _get(url, source["hosts"], http_get)
        for tee in _parse_slope_fragment(fragment, link["name"]):
            key = (tee["name"], tee["gender"])
            if key in seen:
                continue
            seen.add(key)
            tees.append(tee)
    if not tees:
        raise LookupError(
            f"CR og slope fra {source['label']} kunne ikke leses. Skjemaet er uendret."
        )
    return {
        "ok": True,
        "source": source["label"],
        "url": source["slope_url"],
        "tees": tees,
        "message": f"CR og slope fra {source['label']}.",
    }


def _source_for(name, facility):
    text = f"{name or ''} {facility or ''}".strip()
    if not text:
        raise LookupError("Skriv banenavn eller anlegg først.")
    hay = f" {_norm(text)} "
    hits = [
        source
        for source in SOURCES
        if any(f" {_norm(alias)} " in hay for alias in source["aliases"])
    ]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise LookupError("Navnet passer flere klubber. Skjemaet er uendret.")
    raise LookupError(
        "Fant ikke et verifisert scorekort for denne banen. Skjemaet er uendret."
    )


def _norm(text):
    text = (text or "").lower().replace("æ", "ae").replace("ø", "o").replace("å", "a")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _host(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise LookupError("Ugyldig kilde.")
    return parsed.hostname.lower().removeprefix("www.")


def _allowed(host, hosts):
    bare = host.lower().removeprefix("www.")
    return bare in {item.lower().removeprefix("www.") for item in hosts}


def _get(url, hosts, http_get):
    if not _allowed(_host(url), hosts):
        raise LookupError("Ugyldig kilde.")
    if http_get is not None:
        return http_get(url)
    try:
        response = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Fore/1.0 (course scorecard)"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LookupError("Klarte ikke å hente siden til klubben. Skjemaet er uendret.") from exc
    if not _allowed(_host(response.url), hosts):
        raise LookupError("Klubbsiden sendte oss et annet sted. Skjemaet er uendret.")
    if len(response.content) > _MAX_BYTES:
        raise LookupError("Svaret fra klubben var for stort. Skjemaet er uendret.")
    response.encoding = response.encoding or "utf-8"
    return response.text


def _cells(fragment):
    packed = []
    for _kind, attrs, raw in _CELL.findall(fragment):
        match = _CLASS.search(attrs or "")
        text = html.unescape(_TAG.sub("", raw)).replace("\xa0", " ").strip()
        packed.append({"class": match.group(1) if match else "", "text": text})
    return packed


def _choose_scorecard(page, query):
    cards = []
    for table in _TABLE.findall(page):
        card = _parse_scorecard_table(table)
        if card is not None:
            cards.append(card)
    if not cards:
        return None
    hay = _norm(query)
    if re.search(r"\b18\b", hay):
        eighteen = [card for card in cards if len(card["holes"]) == 18]
        if eighteen:
            return eighteen[0]
    if re.search(r"\b9\b", hay):
        nine = [card for card in cards if len(card["holes"]) == 9]
        if nine:
            return nine[0]
    return max(cards, key=lambda card: len(card["holes"]))


def _parse_scorecard_table(table):
    header_html = re.search(r"<thead>(.*?)</thead>", table, re.I | re.S)
    body_html = re.search(r"<tbody>(.*?)</tbody>", table, re.I | re.S)
    if header_html is None or body_html is None:
        return None
    header = _cells(header_html.group(1))
    tee_at = [index for index, cell in enumerate(header) if "tee-" in cell["class"]]
    index_at = next((index for index, cell in enumerate(header) if "scc-ind" in cell["class"]), None)
    par_at = next((index for index, cell in enumerate(header) if "scc-par" in cell["class"]), None)
    if not tee_at or index_at is None or par_at is None:
        return None
    meter_at = tee_at[0]
    holes = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", body_html.group(1), re.I | re.S):
        cells = _cells(row_html)
        if not cells or not cells[0]["text"].isdigit():
            continue
        number = int(cells[0]["text"])
        try:
            par = int(_at(cells, par_at))
            stroke_index = int(_at(cells, index_at))
            meters = int(_at(cells, meter_at))
        except ValueError:
            return None
        holes.append({
            "number": number,
            "par": par,
            "stroke_index": stroke_index,
            "meters": meters,
        })
    if not _consistent(holes):
        return None
    return {"meters_tee": header[meter_at]["text"], "holes": holes}


def _at(cells, index):
    if index >= len(cells):
        raise ValueError
    return cells[index]["text"]


def _consistent(holes):
    if not holes or len(holes) > 54:
        return False
    if [hole["number"] for hole in holes] != list(range(1, len(holes) + 1)):
        return False
    indexes = []
    for hole in holes:
        if hole["par"] < 3 or hole["par"] > 6:
            return False
        if hole["meters"] < 30 or hole["meters"] > 750:
            return False
        indexes.append(hole["stroke_index"])
    return sorted(indexes) == list(range(1, len(holes) + 1))


def _slope_tee_links(page):
    links = []
    for tag in _SELTEE.findall(page):
        attrs = dict(_ATTR.findall(tag))
        name = re.search(r">([^<]+)</a>", tag, re.I)
        course = attrs.get("rel", "").strip()
        ref = attrs.get("data-send", "").strip()
        tee_name = name.group(1).strip() if name else ""
        if course and ref and tee_name:
            links.append({"course": course, "ref": ref, "name": tee_name})
    return links


def _parse_slope_fragment(fragment, tee_name):
    shown = re.search(r'class="thistee[^"]*">([^<]+)', fragment)
    name = shown.group(1).strip() if shown else tee_name
    tees = []
    for block in re.split(r"<h3>", fragment, flags=re.I)[1:]:
        heading = re.match(r"\s*([^<]+)</h3>", block, re.I)
        par = re.search(r"Par:\s*(\d+)", block)
        rating = re.search(
            r"CR/Slope:\s*(?:<br\s*/?>)?\s*([0-9]+(?:[.,][0-9]+)?)\s*/\s*(\d+)",
            block,
            re.I,
        )
        if heading is None or par is None or rating is None:
            continue
        gender = _GENDER.get(heading.group(1).strip().lower())
        if gender is None:
            continue
        course_rating = float(rating.group(1).replace(",", "."))
        slope = int(rating.group(2))
        tee_par = int(par.group(1))
        if not (50 <= course_rating <= 85 and 55 <= slope <= 155 and 27 <= tee_par <= 80):
            continue
        tees.append({
            "name": name,
            "gender": gender,
            "par": tee_par,
            "course_rating": course_rating,
            "slope_rating": slope,
        })
    return tees
