#!/usr/bin/env python3
"""`district` CLI: events, movies, showtimes, restaurants and bookings on District by Zomato (district.in).
Python 3.9+, standard library only.

Every command prints JSON to stdout; errors go to stderr as {"error": ...} with exit code 1.
Guest mode needs no login. `login` stores session cookies in ~/.district-skill/session.json (0600).
"""
from __future__ import annotations

import argparse
import html
import http.cookiejar
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

SITE = "https://www.district.in"
GW = f"{SITE}/gw"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
STATE_DIR = Path(os.environ.get("DISTRICT_HOME", Path.home() / ".district-skill"))
STATE_FILE = STATE_DIR / "state.json"      # device id, last-used location, pending login phone
COOKIE_FILE = STATE_DIR / "session.cookies"  # login session; never print or share

CITIES = {
    "mumbai": (19.076, 72.8777), "delhi": (28.6139, 77.209), "new delhi": (28.6139, 77.209),
    "bengaluru": (12.9716, 77.5946), "bangalore": (12.9716, 77.5946), "hyderabad": (17.385, 78.4867),
    "chennai": (13.0827, 80.2707), "kolkata": (22.5726, 88.3639), "pune": (18.5204, 73.8567),
    "gurugram": (28.4595, 77.0266), "gurgaon": (28.4595, 77.0266), "noida": (28.5355, 77.391),
    "ahmedabad": (23.0225, 72.5714), "jaipur": (26.9124, 75.7873), "chandigarh": (30.7333, 76.7794),
}


class Err(Exception):
    pass


# ---------------------------------------------------------------- state / http
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(st: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE_FILE.write_text(json.dumps(st))
    STATE_FILE.chmod(0o600)


STATE = load_state()
if "device_id" not in STATE:
    STATE["device_id"] = str(uuid.uuid4())
    save_state(STATE)

JAR = http.cookiejar.MozillaCookieJar(str(COOKIE_FILE))
try:
    JAR.load(ignore_discard=True, ignore_expires=True)
except (OSError, http.cookiejar.LoadError):
    pass
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(JAR))


def save_cookies() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    JAR.save(ignore_discard=True, ignore_expires=True)
    COOKIE_FILE.chmod(0o600)


def logged_in() -> bool:
    return any(c.domain.endswith("district.in") for c in JAR) and bool(STATE.get("logged_in"))


def headers(loc: dict | None = None) -> dict:
    h = {
        "User-Agent": UA, "Content-Type": "application/json", "x-client-id": "district-web",
        "x-device-id": STATE["device_id"], "x-app-type": "ed_web", "x-app-version": "11.11.1",
        "x-is-events-supported": "true", "x-is-movies-supported": "true", "x-is-dining-supported": "true",
        "x-is-granular-loc": "false", "x-gps-permission-given": "0",
    }
    if not logged_in():
        h["x-guest-token"] = "1212"  # constant the site sends for logged-out users
    if loc:
        h.update({
            "x-city-id": str(loc.get("city_id", "")), "x-pcity-id": str(loc.get("p_city_id", "")),
            "x-pcity-key": str(loc.get("p_city_key", "")), "x-pstate-key": str(loc.get("p_state_key", "")),
            "x-country-id": str(loc.get("country_id", "1")),
            "x-user-lat": str(loc["user_lat"]), "x-user-lng": str(loc["user_lng"]),
            "x-gps-lat": str(loc["gps_lat"]), "x-gps-lng": str(loc["gps_lng"]),
        })
    return h


def request(method: str, url: str, body: dict | None = None, hdrs: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs or {"User-Agent": UA})
    try:
        with OPENER.open(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise Err(f"Network error: {e.reason}")


def gw(path: str, body: dict | None = None, loc: dict | None = None, method: str = "POST") -> dict:
    status, raw = request(method, GW + path, body if method == "POST" else None, headers(loc))
    if status == 403 and logged_in():  # session expired -> try refresh once
        s2, _ = request("POST", GW + "/auth/refresh_token", {}, headers())
        if s2 == 200:
            save_cookies()
            status, raw = request(method, GW + path, body if method == "POST" else None, headers(loc))
    try:
        data = json.loads(raw or b"{}")
    except ValueError:
        raise Err(f"District API {path} returned non-JSON (HTTP {status})")
    if status in (401, 403):
        raise Err("Not logged in or session expired. Run: district.py login start <phone>")
    if status >= 400:
        if isinstance(data, dict):
            st = data.get("status")
            msg = (st.get("message") if isinstance(st, dict) else st) or data.get("message") or str(data)[:200]
        else:
            msg = str(data)[:200]
        raise Err(f"District API {path} HTTP {status}: {msg}")
    return data


def page(url: str) -> str:
    status, raw = request("GET", url)
    if status != 200:
        raise Err(f"Page not found (HTTP {status}): {url}")
    return raw.decode("utf8", "replace")


def ld_json(text: str) -> list:
    out = []
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', text, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        out.extend(d.get("@graph", [d]) if isinstance(d, dict) else d)
    return out


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>|&nbsp;", " ", s or "")).strip() if isinstance(s, str) else s


# ---------------------------------------------------------------- location
_ALIASES = {"bangalore": "bengaluru", "gurgaon": "gurugram", "bombay": "mumbai", "calcutta": "kolkata",
            "madras": "chennai", "new delhi": "delhi"}


def _norm(t: str) -> str:
    t = t.lower().strip()
    return _ALIASES.get(t, t)


def place_search(text: str) -> list[dict]:
    """Search District's place autocomplete. For 'Area, City' the area is searched and results are
    ranked so matches on both area and city come first (raw top hits are often a different city)."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    area, rest = (parts[0] if parts else text), [_norm(p) for p in parts[1:]]
    d = gw("/web/get_location_search", {"searched_text": area})
    ents = [e for e in d.get("entities") or [] if e.get("lat") is not None and e.get("long") is not None]

    def score(e: dict) -> tuple:
        full = _norm(e.get("fullname") or "")
        full = " ".join(_norm(w) for w in re.split(r"[,\s]+", full))
        city_hit = bool(rest) and all(any(r in full for r in (c, _ALIASES.get(c, c))) for c in rest)
        title_hit = _norm(area) in _norm(e.get("title") or "")
        subzone = e.get("entity_type") == "LOCATION_ENTITY_TYPE_SUBZONE"
        return (not city_hit, not title_hit, not subzone)

    return sorted(ents, key=score)


def resolve(args) -> tuple[float, float, str | None]:
    """Location must be given explicitly each time (no remembered default): --near/--city TEXT or --lat/--lng."""
    if args.lat is not None and args.lng is not None:
        return args.lat, args.lng, None
    if args.city:
        key = args.city.strip().lower()
        if key in CITIES:
            lat, lng = CITIES[key]
            print(f"# location: {args.city} ({lat}, {lng})", file=sys.stderr)
            return lat, lng, key
        hits = place_search(args.city)
        if not hits:
            raise Err(f"Could not find a place matching '{args.city}'. Ask the user for a more specific area or city.")
        h = hits[0]
        print(f"# location: {h.get('fullname') or h.get('title')} ({h['lat']}, {h['long']})", file=sys.stderr)
        return h["lat"], h["long"], None
    raise Err("Location required: ask the user where they are, then pass --near \"<area, city>\" (or --lat/--lng).")


def location(lat: float, lng: float) -> dict:
    d = gw("/web/pre_home", {"gps_lat": lat, "gps_lng": lng, "user_lat": lat, "user_lng": lng})
    loc = d.get("location_data") or {}
    for k, v in (("user_lat", lat), ("user_lng", lng), ("gps_lat", lat), ("gps_lng", lng)):
        loc.setdefault(k, v)
    return loc


def discover(lat, lng, layout):
    loc = location(lat, lng)
    body = {"layout_type": layout, "request_type": "tab_switch", "location": {
        "city_id": int(loc.get("city_id") or 0) or 57, "user_lat": lat, "user_lng": lng,
        "gps_lat": lat, "gps_lng": lng}}
    return (gw("/web/get_discovery_results", body, loc).get("EDSResponse") or {}).get("rails") or []


# ---------------------------------------------------------------- commands
def cmd_search(a):
    lat, lng, _ = resolve(a)
    res = gw("/web/search", {"get_search_results_request_type": 1, "post_body": {"hp_selected_tab_id": "home_v2"},
                             "search_id": str(uuid.uuid4()), "keyword": a.keyword, "tab_id": "all"},
             location(lat, lng)).get("results") or []
    out = []
    for r in res[: a.limit]:
        md, t = r.get("metadata") or {}, r.get("entity_type", "").removeprefix("EntityType")
        item = {"type": t, "title": r.get("display_title"), "id": r.get("id")}
        if t == "Event":
            item.update(slug=md.get("slug"), venue=md.get("venue_name"), locality=md.get("venue_locality"),
                        when=md.get("date_string_v2"),
                        url=f"{SITE}/events/{md.get('slug')}-buy-tickets" if md.get("slug") else None)
        elif t == "Res":
            item.update(type="Restaurant", address=md.get("address"), rating=md.get("rating"),
                        cost_for_two=md.get("cft"), distance_km=md.get("dist"), seo_path=md.get("seo_url"),
                        url=f"{SITE}/dining{md['seo_url']}" if md.get("seo_url") else None)
        else:
            item["metadata"] = {k: v for k, v in md.items() if v and k not in ("app_deeplink",)}
        out.append(item)
    return out


def cmd_events(a):
    lat, lng, _ = resolve(a)
    seen, out = set(), []
    for rail in discover(lat, lng, "events_home_v2"):
        for it in rail.get("items") or []:
            e = (it.get("ItemDetails") or {}).get("EventData")
            if not e or not e.get("event_slug") or e["event_slug"] in seen:
                continue
            seen.add(e["event_slug"])
            out.append({"name": e.get("name"), "slug": e["event_slug"], "venue": e.get("venue_name"),
                        "locality": e.get("locality"), "city": e.get("city"),
                        "when": e.get("date_string_v2") or e.get("date_string"), "price": e.get("price_string"),
                        "url": f"{SITE}/events/{e['event_slug']}-buy-tickets"})
    return out[: a.limit]


def cmd_event(a):
    slug = a.slug.removesuffix("-buy-tickets")
    url = f"{SITE}/events/{slug}-buy-tickets"
    items = ld_json(page(url))
    ev = next((i for i in items if i.get("@type") == "Event"), None)
    if not ev:
        raise Err("Could not parse event page.")
    faq = next((i for i in items if i.get("@type") == "FAQPage"), {})
    return {"name": ev.get("name"), "description": clean(ev.get("description")), "start": ev.get("startDate"),
            "end": ev.get("endDate"), "status": ev.get("eventStatus"), "location": ev.get("location"),
            "offers": ev.get("offers"), "performers": ev.get("performer"),
            "faq": [{"q": q["name"], "a": clean(q["acceptedAnswer"]["text"])} for q in faq.get("mainEntity", [])],
            "url": url}


def cmd_movies(a):
    lat, lng, _ = resolve(a)
    return movies_at(lat, lng)[: a.limit]


def movies_at(lat, lng):
    seen, out = set(), []
    for rail in discover(lat, lng, "movies_home"):
        for it in rail.get("items") or []:
            m = (it.get("ItemDetails") or {}).get("MovieData")
            if not m or m.get("movie_id") in seen:
                continue
            seen.add(m["movie_id"])
            v = m.get("movie_variants") or []
            out.append({"name": m.get("name"), "movie_id": m["movie_id"], "genres": m.get("genres"),
                        "duration_min": m.get("Duration"), "censor": m.get("censor"),
                        "languages": sorted({x["language"] for x in v if x.get("language")}),
                        "formats": sorted({x["format"] for x in v if x.get("format")})})
    return out


def cmd_showtimes(a):
    """Showtimes for a movie in a city. Booking happens on district.in via the returned seat_layout_url."""
    lat, lng, name = resolve(a)
    city = (name or location(lat, lng).get("city_name") or "").lower().replace(" ", "-")
    if not city:
        raise Err("Could not determine city slug; pass --city.")
    mid = a.movie_id
    if not mid.isdigit():  # allow a movie name: look it up in the now-showing list
        hits = [m for m in movies_at(lat, lng) if mid.lower() in m["name"].lower()]
        if not hits:
            raise Err(f"No now-showing movie matches '{mid}'. Try the `movies` command.")
        mid = hits[0]["movie_id"]
    text = page(f"{SITE}/movies/movie-movie-tickets-in-{city}-MV{mid}")
    shows = [i for i in ld_json(text) if i.get("@type") == "ScreeningEvent"]
    by_cinema: dict[str, dict] = {}
    for s in shows:
        loc = s.get("location") or {}
        cname = loc.get("name", "?")
        if a.cinema and a.cinema.lower() not in cname.lower():
            continue
        if a.date and not (s.get("startDate") or "").startswith(a.date):
            continue
        offer = s.get("offers") or {}
        g = loc.get("geo") or {}
        dist = None
        if g.get("latitude") is not None and g.get("longitude") is not None:
            p1, p2 = math.radians(lat), math.radians(g["latitude"])
            h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(g["longitude"] - lng) / 2) ** 2
            dist = round(12742 * math.asin(math.sqrt(h)), 1)
        c = by_cinema.setdefault(cname, {"cinema": cname, "distance_km": dist,
                                         "address": (loc.get("address") or {}).get("streetAddress"),
                                         "cinema_url": loc.get("url"), "shows": []})
        c["shows"].append({"start": s.get("startDate"), "format": s.get("videoFormat"), "price_inr": offer.get("price"),
                           "available": "InStock" in str(offer.get("availability")),
                           "seat_layout_url": offer.get("url")})
    cinemas = sorted(by_cinema.values(), key=lambda c: (c["distance_km"] is None, c["distance_km"] or 0))[: a.limit]
    for c in cinemas:
        c["shows"].sort(key=lambda x: x["start"] or "")
    return {"movie_id": mid, "city": city, "cinemas": cinemas,
            "note": "Page lists a subset of sessions per cinema. Open seat_layout_url in a browser to pick seats and pay."}


def cmd_restaurant(a):
    path = a.path.strip()
    path = re.sub(r"^https?://[^/]+", "", path)
    path = path.removeprefix("/dining")
    url = f"{SITE}/dining{path if path.startswith('/') else '/' + path}"
    items = ld_json(page(url))
    r = next((i for i in items if i.get("@type") in ("Restaurant", "BarOrPub", "CafeOrCoffeeShop", "FoodEstablishment")), None)
    if not r:
        raise Err("Could not parse restaurant page.")
    return {"name": r.get("name"), "cuisines": r.get("servesCuisine"), "price_range": r.get("priceRange"),
            "phone": r.get("telephone"), "address": (r.get("address") or {}).get("streetAddress"),
            "geo": r.get("geo"), "rating": r.get("aggregateRating"), "hours": r.get("openingHoursSpecification"),
            "images": (r.get("image") or [])[:3] if isinstance(r.get("image"), list) else r.get("image"), "url": url}


def cmd_places(a):
    return [{"name": e.get("fullname") or e.get("title"), "lat": e["lat"], "lng": e["long"]}
            for e in place_search(a.query)[: a.limit]]


def cmd_install_skills(a):
    from .installer import install
    return install(a.dest, a.only)


# ---- login (OTP). Credentials never touch disk except the session cookies District returns.
def cmd_login(a):
    if a.action == "start":
        if not a.phone or not re.fullmatch(r"\d{6,15}", a.phone):
            raise Err("Provide digits-only phone number, e.g. login start 9876543210 [--country-code 91]")
        gw("/auth/generate_otp", {"phone_number": a.phone, "country_code": a.country_code})
        STATE.update(pending_phone=a.phone, pending_cc=a.country_code)
        save_state(STATE)
        return {"ok": True, "message": f"OTP sent to +{a.country_code} {a.phone}. Run: login verify <6-digit-otp>"}
    if a.action == "verify":
        if not STATE.get("pending_phone"):
            raise Err("No login in progress. Run: login start <phone>")
        if not a.phone or not re.fullmatch(r"\d{6}", a.phone):
            raise Err("OTP must be 6 digits: login verify 123456")
        d = gw("/auth/validate_otp", {"phone_number": STATE["pending_phone"], "country_code": STATE["pending_cc"],
                                       "otp": a.phone})
        msg = (d.get("status") or {}).get("message")
        if msg:
            raise Err(f"Login failed: {msg}")
        STATE.pop("pending_phone", None)
        STATE["logged_in"] = True
        save_state(STATE)
        save_cookies()
        prof = gw("/consumer/profile/billing/details", method="GET")
        u = (prof.get("user_data") or {})
        if not u.get("user_id"):
            STATE["logged_in"] = False
            save_state(STATE)
            raise Err("OTP accepted but no user session was returned.")
        return {"ok": True, "name": u.get("name"), "phone": u.get("phone_number")}
    if a.action == "status":
        if not logged_in():
            return {"logged_in": False}
        try:
            u = gw("/consumer/profile/billing/details", method="GET").get("user_data") or {}
        except Err:
            return {"logged_in": False, "note": "session expired"}
        return {"logged_in": bool(u.get("user_id")), "name": u.get("name")}
    if a.action == "logout":
        try:
            gw("/logout", {})
        except Err:
            pass
        for p in (COOKIE_FILE,):
            p.unlink(missing_ok=True)
        STATE.pop("logged_in", None)
        save_state(STATE)
        return {"ok": True}
    raise Err("login action must be: start | verify | status | logout")


def cmd_bookings(a):
    if not logged_in():
        raise Err("Login required. Run: login start <phone>")
    kinds = [a.kind.lower()] if a.kind else ["movies", "events"]
    out = {}
    for k in kinds:
        d = gw("/consumer/web/order_history", {"order_type": k})
        # Response is {"cart_type": ..., "page_identifier": ...} plus order rows when the user has any.
        rows = {x: v for x, v in d.items() if x not in ("cart_type", "page_identifier")}
        out[k] = rows if rows else "no orders found"
    return out


COMMANDS = {"search": cmd_search, "events": cmd_events, "event": cmd_event, "movies": cmd_movies,
            "showtimes": cmd_showtimes, "restaurant": cmd_restaurant, "login": cmd_login, "bookings": cmd_bookings,
            "places": cmd_places, "install-skills": cmd_install_skills}


def main() -> int:
    p = argparse.ArgumentParser(prog="district", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def loc_args(sp):
        sp.add_argument("--near", "--city", dest="city", help="area or city, e.g. \"Koramangala, Bengaluru\"")
        sp.add_argument("--lat", type=float)
        sp.add_argument("--lng", type=float)

    s = sub.add_parser("search"); s.add_argument("keyword"); loc_args(s); s.add_argument("--limit", type=int, default=15)
    s = sub.add_parser("events"); loc_args(s); s.add_argument("--limit", type=int, default=25)
    s = sub.add_parser("event"); s.add_argument("slug")
    s = sub.add_parser("movies"); loc_args(s); s.add_argument("--limit", type=int, default=30)
    s = sub.add_parser("showtimes"); s.add_argument("movie_id", help="numeric id or part of the title"); loc_args(s)
    s.add_argument("--cinema"); s.add_argument("--date", help="YYYY-MM-DD"); s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("restaurant"); s.add_argument("path", help="seo_path from search, e.g. /mumbai/toit-lower-parel")
    s = sub.add_parser("login"); s.add_argument("action", choices=["start", "verify", "status", "logout"])
    s.add_argument("phone", nargs="?", help="phone number (start) or 6-digit OTP (verify)")
    s.add_argument("--country-code", default="91")
    s = sub.add_parser("places", help="look up an area/city to confirm the location with the user")
    s.add_argument("query"); s.add_argument("--limit", type=int, default=5)
    s = sub.add_parser("install-skills", help="copy the bundled agent skills into a skills directory")
    s.add_argument("--dest", help="default: ~/.claude/skills"); s.add_argument("--only", nargs="*", help="skill names")
    s = sub.add_parser("bookings"); s.add_argument("--kind", help="movies or events (default: both)")
    a = p.parse_args()
    try:
        out = COMMANDS[a.cmd](a)
    except Err as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
