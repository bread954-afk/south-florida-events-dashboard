import json

from bs4 import BeautifulSoup

from scripts.collectors.base import CollectorResult, HttpClient
from scripts.events.normalize import normalize_event, parse_datetime


def flatten_jsonld(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from flatten_jsonld(item)
    elif isinstance(obj, dict):
        if "@graph" in obj:
            yield from flatten_jsonld(obj["@graph"])
        yield obj


def _text(value) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("@value") or "")
    return str(value or "")


def _category(obj: dict) -> str:
    name = _text(obj.get("name"))
    desc = _text(obj.get("description"))
    typ = obj.get("@type")
    type_text = " ".join(map(str, typ if isinstance(typ, list) else [typ]))
    low = f"{name} {desc} {type_text}".lower()
    for label, needle in (
        ("Comedy", "comedy"),
        ("Sports", "sports"),
        ("Sports", "sportsevent"),
        ("Concert / Music", "musicevent"),
        ("Concert / Music", "concert"),
        ("Nightlife / Party", "nightclub"),
        ("Nightlife / Party", "party"),
        ("Festival", "festival"),
        ("Food / Dining", "food"),
        ("Art / Museum", "museum"),
        ("Art / Museum", "art"),
        ("Family", "family"),
        ("Market", "market"),
    ):
        if needle in low:
            return label
    return "Event"


def _raw_from_jsonld(obj: dict) -> dict | None:
    event_type = obj.get("@type")
    types = event_type if isinstance(event_type, list) else [event_type]
    if not any(str(t).lower().endswith("event") for t in types if t):
        return None

    location = obj.get("location") or {}
    venue = ""
    city = ""
    if isinstance(location, dict):
        venue = _text(location.get("name")).strip()
        address = location.get("address") or {}
        if isinstance(address, dict):
            city = _text(address.get("addressLocality")).strip()

    offers = obj.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    cost = "Check source"
    event_url = obj.get("url")
    if isinstance(offers, dict):
        price = offers.get("price")
        currency = offers.get("priceCurrency", "USD")
        event_url = offers.get("url") or event_url
        if price not in (None, ""):
            cost = f"{currency} {price}"
        elif "free" in str(offers.get("availability", "")).lower():
            cost = "Free"

    return {
        "name": _text(obj.get("name")),
        "start": obj.get("startDate"),
        "venue": venue,
        "city": city,
        "cost": cost,
        "url": event_url,
        "category": _category(obj),
    }


def parse_jsonld_html(
    html: str,
    source: dict,
    page_url: str,
    target_year: int,
    target_month: int,
) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or tag.get_text() or "{}")
        except json.JSONDecodeError:
            continue

        for obj in flatten_jsonld(data):
            raw = _raw_from_jsonld(obj)
            if raw is None:
                continue
            event = normalize_event(raw, source, page_url)
            if event is None:
                continue
            parsed = parse_datetime(event["date"])
            if parsed and parsed.year == target_year and parsed.month == target_month:
                events.append(event)

    return events


def collect_jsonld(
    source: dict,
    target_year: int,
    target_month: int,
    client: HttpClient | None = None,
) -> CollectorResult:
    client = client or HttpClient()
    try:
        response = client.get(source["url"])
        events = parse_jsonld_html(
            response.text,
            source,
            source["url"],
            target_year,
            target_month,
        )
        return CollectorResult(events=events, status="ok")
    except Exception as exc:
        return CollectorResult(status="http_error", message=str(exc))
