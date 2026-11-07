"""Fetch scorecard and tee ratings from a club page, then slope.no, then Datagolf.

Only hosts listed below are contacted. A page that cannot be parsed is
rejected, so the form is never filled with guessed numbers. slope.no is used
when the club page has no readable card. Datagolf is the Portuguese course
list and is used only when slope.no has no match. The message says which
source was used.
"""

import html
import re
import unicodedata
from urllib.parse import urlencode, urlparse

import requests


class LookupError(Exception):
    """The club page could not be used. The message is safe to show."""


class _Miss(LookupError):
    """The directory answered, and the course was not in it."""


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
_SLOPE_GENDER = {
    "menn": "Herre",
    "herrer": "Herre",
    "men": "Herre",
    "damer": "Dame",
    "kvinner": "Dame",
    "women": "Dame",
}
_SLOPE_DIRECTORY = "https://slope.no/baner/"
_SLOPE_HOSTS = ("slope.no",)
_DATAGOLF_DIRECTORY = (
    "https://scoring-pt.datagolf.pt/scripts/all_courses.asp?ack=8428ACK987&club=ALL"
)
_DATAGOLF_HOSTS = ("scoring-pt.datagolf.pt",)
_DATAGOLF_COLORS = {
    "FFFFFF": "Hvit",
    "FFFF00": "Gul",
    "0000FF": "Blå",
    "FF0000": "Rød",
    "000000": "Sort",
    "008000": "Grønn",
    "A000A0": "Lilla",
}
_DATAGOLF_GENDER = {"homens": "Herre", "senhoras": "Dame"}
_COURSE_MISS = (
    "Fant ikke banen på klubbsiden, på slope.no eller på Datagolf. "
    "Skjemaet er uendret."
)
_CARD_MISS = (
    "Fant ikke scorekortet på klubbsiden, på slope.no eller på Datagolf. "
    "Skjemaet er uendret."
)
_RATING_MISS = (
    "Fant ikke CR og slope på klubbsiden, på slope.no eller på Datagolf. "
    "Skjemaet er uendret."
)
_SLOPE_SKIP = {"kart", "greenfee"}
_NAME_STOP = {
    "golf",
    "golfklubb",
    "golfklub",
    "golfklubben",
    "golfclub",
    "klubb",
    "bane",
    "banen",
    "course",
    "club",
}
_DATAGOLF_STOP = _NAME_STOP | {"golfe", "clube", "campo"}
_COURSE_LINK = re.compile(
    r'href="(https://slope\.no/baner/([a-z0-9-]+)/)"[^>]*>([^<]+)</a>',
    re.I,
)
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
    _require_query(name, facility)
    source = _club_source(name, facility)
    club_error = None
    if source is not None:
        try:
            return _club_scorecard(source, name, facility, http_get)
        except LookupError as exc:
            club_error = exc
    try:
        return _slope_scorecard(name, facility, http_get)
    except _Miss:
        pass
    except LookupError as exc:
        if club_error is not None:
            raise LookupError(_CARD_MISS) from club_error
        raise exc
    try:
        return _datagolf_scorecard(name, facility, http_get)
    except _Miss as exc:
        if club_error is not None:
            raise LookupError(_CARD_MISS) from club_error
        raise LookupError(_COURSE_MISS) from exc


def _fetch_ratings(name, facility, http_get):
    _require_query(name, facility)
    source = _club_source(name, facility)
    club_error = None
    if source is not None:
        try:
            return _club_ratings(source, http_get)
        except LookupError as exc:
            club_error = exc
    try:
        return _slope_ratings(name, facility, http_get)
    except _Miss:
        pass
    except LookupError as exc:
        if club_error is not None:
            raise LookupError(_RATING_MISS) from club_error
        raise exc
    try:
        return _datagolf_ratings(name, facility, http_get)
    except _Miss as exc:
        if club_error is not None:
            raise LookupError(_RATING_MISS) from club_error
        raise LookupError(_COURSE_MISS) from exc


def _require_query(name, facility):
    if not f"{name or ''} {facility or ''}".strip():
        raise LookupError("Skriv banenavn eller anlegg først.")


def _club_source(name, facility):
    hay = f" {_norm((name or '') + ' ' + (facility or ''))} "
    hits = [
        source
        for source in SOURCES
        if any(f" {_norm(alias)} " in hay for alias in source["aliases"])
    ]
    if len(hits) > 1:
        raise LookupError("Navnet passer flere klubber. Skjemaet er uendret.")
    return hits[0] if hits else None


def _club_scorecard(source, name, facility, http_get):
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


def _club_ratings(source, http_get):
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


def _slope_course(name, facility, http_get):
    page = _get(_SLOPE_DIRECTORY, _SLOPE_HOSTS, http_get, who="slope.no")
    query = _name_tokens(f"{name or ''} {facility or ''}")
    hits = []
    seen = set()
    for url, slug, title in _COURSE_LINK.findall(page):
        if slug in _SLOPE_SKIP or url in seen:
            continue
        seen.add(url)
        title = html.unescape(title).strip()
        tokens = _name_tokens(title)
        if tokens and all(token in query for token in tokens):
            hits.append({"name": title, "url": url})
    if len(hits) > 1:
        raise LookupError("Navnet passer flere baner på slope.no. Skjemaet er uendret.")
    if not hits:
        raise _Miss(
            "Fant ikke banen på klubbsiden eller på slope.no. Skjemaet er uendret."
        )
    return hits[0]


def _name_tokens(text):
    return [
        token
        for token in _norm(text).split()
        if len(token) >= 4 and token not in _NAME_STOP
    ]


def _slope_scorecard(name, facility, http_get):
    course = _slope_course(name, facility, http_get)
    page = _get(course["url"], _SLOPE_HOSTS, http_get, who="slope.no")
    card = _choose_slope_card(page)
    if card is None:
        raise LookupError("Scorekortet fra slope.no kunne ikke leses. Skjemaet er uendret.")
    return {
        "ok": True,
        "source": "slope.no",
        "url": course["url"],
        "meters_tee": card["tee"],
        "hole_count": len(card["holes"]),
        "holes": card["holes"],
        "message": (
            f"Scorekort fra slope.no ({course['name']}). "
            f"Meter er fra utslag {card['tee']}. "
            "Dette er ikke klubbens egen side, så rett det som ikke stemmer."
        ),
    }


def _slope_ratings(name, facility, http_get):
    course = _slope_course(name, facility, http_get)
    page = _get(course["url"], _SLOPE_HOSTS, http_get, who="slope.no")
    tees = _parse_slope_no_ratings(page)
    if not tees:
        raise LookupError("CR og slope fra slope.no kunne ikke leses. Skjemaet er uendret.")
    return {
        "ok": True,
        "source": "slope.no",
        "url": course["url"],
        "tees": tees,
        "message": (
            f"CR og slope fra slope.no ({course['name']}). "
            "Dette er ikke klubbens egen side, så rett det som ikke stemmer."
        ),
    }


def _datagolf_tokens(text):
    return [
        token
        for token in _norm(text).split()
        if len(token) >= 3 and token not in _DATAGOLF_STOP
    ]


def _datagolf_text(raw):
    return html.unescape(raw).replace("\xa0", " ").replace("&nbsp;", " ").strip()


def _datagolf_directory(page):
    courses = []
    seen = set()
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, re.S | re.I):
        links = re.findall(
            r'href="course\.asp\?ncourse=(\d+)&(?:amp;)?ack=([^"&]+)&(?:amp;)?club=ALL"[^>]*>\s*([^<]*)',
            row,
            re.I,
        )
        count = re.search(r"<td[^>]*>\s*(\d+)\s*(?:&nbsp;)?\s*</td>\s*$", row, re.I)
        if len(links) < 2 or count is None:
            continue
        course_id, ack, short = links[0]
        full = links[1][2]
        if course_id in seen:
            continue
        seen.add(course_id)
        layouts = int(count.group(1))
        if layouts < 1 or layouts > 6:
            continue
        courses.append({
            "id": course_id,
            "ack": ack,
            "short": _datagolf_text(short),
            "full": _datagolf_text(full),
            "layouts": layouts,
        })
    return courses


def _datagolf_match(course, query):
    for label in (course["short"], course["full"]):
        tokens = _datagolf_tokens(label)
        if tokens and all(token in query for token in tokens):
            return True
    return False


def _datagolf_course(name, facility, http_get):
    page = _get(_DATAGOLF_DIRECTORY, _DATAGOLF_HOSTS, http_get, who="Datagolf")
    query = _datagolf_tokens(f"{name or ''} {facility or ''}")
    hits = [course for course in _datagolf_directory(page) if _datagolf_match(course, query)]
    if len(hits) > 1:
        raise LookupError("Navnet passer flere baner på Datagolf. Skjemaet er uendret.")
    if not hits:
        raise _Miss("Fant ikke banen på Datagolf. Skjemaet er uendret.")
    return hits[0], query


def _datagolf_card_url(course, layout):
    return "https://scoring-pt.datagolf.pt/scripts/show_card.asp?" + urlencode({
        "Club": "ALL",
        "ack": course["ack"],
        "ncourse": course["id"] + "-" + str(layout),
        "stat": "Y",
    })


def _datagolf_cards(course, http_get):
    cards = []
    for layout in range(1, course["layouts"] + 1):
        url = _datagolf_card_url(course, layout)
        try:
            page = _get(url, _DATAGOLF_HOSTS, http_get, who="Datagolf")
        except LookupError:
            continue
        card = _parse_datagolf_card(page)
        if card is not None:
            card["url"] = url
            cards.append(card)
    return cards


def _choose_datagolf_card(cards, query, layouts):
    if not cards:
        raise LookupError("Scorekortet fra Datagolf kunne ikke leses. Skjemaet er uendret.")
    if layouts == 1 and len(cards) == 1:
        return cards[0]
    hits = []
    for card in cards:
        tokens = _datagolf_tokens(card["title"])
        if tokens and all(token in query for token in tokens):
            hits.append(card)
    if len(hits) != 1:
        raise LookupError("Navnet passer flere baner på Datagolf. Skjemaet er uendret.")
    return hits[0]


def _datagolf_scorecard(name, facility, http_get):
    course, query = _datagolf_course(name, facility, http_get)
    card = _choose_datagolf_card(_datagolf_cards(course, http_get), query, course["layouts"])
    if not card["holes"]:
        raise LookupError("Scorekortet fra Datagolf kunne ikke leses. Skjemaet er uendret.")
    return {
        "ok": True,
        "source": "Datagolf",
        "url": card["url"],
        "meters_tee": card["meters_tee"],
        "hole_count": len(card["holes"]),
        "holes": card["holes"],
        "message": (
            f"Scorekort fra Datagolf ({card['title']}). "
            f"Meter er fra utslag {card['meters_tee']}. "
            "Dette er ikke klubbens egen side, så rett det som ikke stemmer."
        ),
    }


def _datagolf_ratings(name, facility, http_get):
    course, query = _datagolf_course(name, facility, http_get)
    card = _choose_datagolf_card(_datagolf_cards(course, http_get), query, course["layouts"])
    if not card["tees"]:
        raise LookupError("CR og slope fra Datagolf kunne ikke leses. Skjemaet er uendret.")
    return {
        "ok": True,
        "source": "Datagolf",
        "url": card["url"],
        "tees": card["tees"],
        "message": (
            f"CR og slope fra Datagolf ({card['title']}). "
            "Dette er ikke klubbens egen side, så rett det som ikke stemmer."
        ),
    }


def _datagolf_cells(row_html):
    cells = []
    for attrs, inner in re.findall(r"<td\b([^>]*)>(.*?)</td>", row_html, re.S | re.I):
        color = re.search(r"bgcolor\s*=\s*\"?#?([0-9A-Fa-f]{6})", attrs, re.I)
        span = re.search(r"colspan\s*=\s*\"?(\d+)", attrs, re.I)
        cells.append({
            "text": _datagolf_text(_TAG.sub("", inner)),
            "color": color.group(1).upper() if color else "",
            "span": int(span.group(1)) if span else 1,
        })
    return cells


def _parse_datagolf_card(page):
    title_match = re.search(r"<b>\s*([^<]+?)\s*</b>", page, re.I)
    table_match = re.search(r'<table\b[^>]*class="preto"[^>]*>(.*?)</table>', page, re.I | re.S)
    if title_match is None or table_match is None:
        return None
    rows = [
        _datagolf_cells(row)
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table_match.group(1), re.S | re.I)
    ]
    rows = [row for row in rows if row]
    if not rows:
        return None
    meter_spans = [cell["span"] for cell in rows[0] if cell["text"].lower() == "metros"]
    if len(meter_spans) != 2 or meter_spans[0] != meter_spans[1] or meter_spans[0] < 1:
        return None
    width = meter_spans[0]
    by_number = {}
    colors = None
    for cells in rows[1:]:
        if not cells[0]["text"].isdigit():
            continue
        if len(cells) < 2 * (width + 3):
            return None
        for side in (0, 1):
            base = side * (width + 3)
            if not cells[base]["text"].isdigit():
                return None
            number = int(cells[base]["text"])
            tee_cells = cells[base + 1:base + 1 + width]
            side_colors = [cell["color"] for cell in tee_cells]
            if colors is None:
                colors = side_colors
            elif side_colors != colors:
                return None
            par = _whole(cells[base + 1 + width]["text"])
            stroke_index = _whole(cells[base + 2 + width]["text"])
            if par is None or stroke_index is None:
                return None
            by_number[number] = {
                "par": par,
                "stroke_index": stroke_index,
                "meters": [_whole(cell["text"]) for cell in tee_cells],
            }
    numbers = sorted(by_number)
    if not numbers or numbers != list(range(1, len(numbers) + 1)):
        return None
    if colors is None or any(len(item["meters"]) != width for item in by_number.values()):
        return None
    tee_par = sum(by_number[number]["par"] for number in numbers)
    played = []
    for index, color in enumerate(colors):
        name = _DATAGOLF_COLORS.get(color)
        if name is None:
            continue
        holes = []
        for number in numbers:
            meters = by_number[number]["meters"][index]
            if meters is None:
                holes = []
                break
            holes.append({
                "number": number,
                "par": by_number[number]["par"],
                "stroke_index": by_number[number]["stroke_index"],
                "meters": meters,
            })
        if holes and _consistent(holes):
            played.append({"name": name, "holes": holes, "sum": sum(hole["meters"] for hole in holes)})
    if not played:
        return None
    chosen = max(played, key=lambda item: item["sum"])
    tees = _datagolf_tees(rows, colors, width, tee_par)
    return {
        "title": _datagolf_text(title_match.group(1)),
        "meters_tee": chosen["name"],
        "holes": chosen["holes"],
        "tees": tees,
    }


def _datagolf_tees(rows, colors, width, tee_par):
    if not (27 <= tee_par <= 80):
        return []
    pending = None
    found = []
    for cells in rows:
        label = cells[0]["text"].lower().rstrip(".")
        if len(cells) < 1 + width + 1:
            pending = None
            continue
        values = cells[1:1 + width]
        if label == "c.rat":
            gender = _DATAGOLF_GENDER.get(re.sub(r"[()]", "", cells[1 + width]["text"]).strip().lower())
            pending = (gender, [_rating(cell["text"]) for cell in values])
            continue
        if label != "slope" or pending is None:
            pending = None
            continue
        gender, ratings = pending
        pending = None
        slopes = [_whole(cell["text"]) for cell in values]
        if gender is None or len(ratings) != width or len(slopes) != width:
            continue
        for color, course_rating, slope in zip(colors, ratings, slopes):
            name = _DATAGOLF_COLORS.get(color)
            if name is None or course_rating is None or slope is None:
                continue
            if not (50 <= course_rating <= 85 and 55 <= slope <= 155):
                continue
            found.append({
                "name": name,
                "gender": gender,
                "par": tee_par,
                "course_rating": course_rating,
                "slope_rating": slope,
            })
    tees = []
    seen = set()
    for tee in found:
        key = (tee["name"], tee["gender"])
        if key in seen:
            continue
        seen.add(key)
        tees.append(tee)
    return tees


def _choose_slope_card(page):
    cards = []
    for part in re.split(r'<div class="ghs-sc-card"', page)[1:]:
        head = re.split(r"<h2\b", part, maxsplit=1)[0]
        name_match = re.search(r'ghs-sc-teename">([^<]+)', head)
        if name_match is None:
            continue
        label = html.unescape(name_match.group(1)).strip()
        holes = []
        broken = False
        for table in re.findall(r'<table class="ghs-sc-table">(.*?)</table>', head, re.S):
            numbers = [int(number) for number in re.findall(r"<th[^>]*>\s*(\d+)\s*</th>", table)]
            pars = _slope_row(table, "ghs-sc-par")
            indexes = _slope_row(table, "ghs-sc-index")
            meters = _slope_row(table, "ghs-sc-length")
            rows = (pars, indexes, meters)
            if not numbers or any(row is None or len(row) != len(numbers) for row in rows):
                broken = True
                break
            for number, par, stroke_index, length in zip(numbers, pars, indexes, meters):
                holes.append({
                    "number": number,
                    "par": par,
                    "stroke_index": stroke_index,
                    "meters": length,
                })
        if broken or not _consistent(holes):
            continue
        tee_name = re.sub(
            r"^(?:herrer|damer|menn|kvinner)\s*,?\s*tee\s+",
            "",
            label,
            flags=re.I,
        ).strip()
        cards.append({"tee": tee_name or label, "holes": holes})
    if not cards:
        return None
    return max(cards, key=lambda card: sum(hole["meters"] for hole in card["holes"]))


def _slope_row(table, klass):
    match = re.search(rf'<tr class="{klass}".*?</tr>', table, re.S)
    if match is None:
        return None
    values = []
    for attrs, raw in re.findall(r"<td([^>]*)>(.*?)</td>", match.group(0), re.S):
        if "ghs-sc-sum" in attrs:
            continue
        text = html.unescape(_TAG.sub("", raw)).replace("\xa0", "").replace(" ", "")
        if not text.isdigit():
            return None
        values.append(int(text))
    return values


def _parse_slope_no_ratings(page):
    tees = []
    seen = set()
    for attrs, inner in re.findall(r"<optgroup\b([^>]*)>(.*?)</optgroup>", page, re.S | re.I):
        label = dict(_ATTR.findall(attrs)).get("label", "")
        gender = _SLOPE_GENDER.get(label.strip().lower())
        if gender is None:
            gender = _SLOPE_GENDER.get(dict(_ATTR.findall(attrs)).get("data-gender", "").lower())
        if gender is None:
            continue
        for option_attrs, raw_name in re.findall(r"<option\b([^>]*)>(.*?)</option>", inner, re.S | re.I):
            option = dict(_ATTR.findall(option_attrs))
            name = html.unescape(_TAG.sub("", raw_name)).strip()
            course_rating = _rating(option.get("data-course", ""))
            slope = _whole(option.get("data-slope", ""))
            tee_par = _whole(option.get("data-par", ""))
            if not name or course_rating is None or slope is None or tee_par is None:
                continue
            if not (50 <= course_rating <= 85 and 55 <= slope <= 155 and 27 <= tee_par <= 80):
                continue
            key = (name, gender)
            if key in seen:
                continue
            seen.add(key)
            tees.append({
                "name": name,
                "gender": gender,
                "par": tee_par,
                "course_rating": course_rating,
                "slope_rating": slope,
            })
    return tees


def _rating(raw):
    text = (raw or "").strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _whole(raw):
    text = (raw or "").strip()
    return int(text) if text.isdigit() else None


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


def _get(url, hosts, http_get, who="klubben"):
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
        raise LookupError(f"Klarte ikke å hente siden til {who}. Skjemaet er uendret.") from exc
    if not _allowed(_host(response.url), hosts):
        raise LookupError(f"Siden til {who} sendte oss et annet sted. Skjemaet er uendret.")
    if len(response.content) > _MAX_BYTES:
        raise LookupError(f"Svaret fra {who} var for stort. Skjemaet er uendret.")
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
