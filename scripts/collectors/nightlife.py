import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.browser import render_html
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html
from scripts.events.normalize import normalize_event, parse_datetime


PROFILES = [
    CardSelectors(card=".event-card", name=".event-title", date=".event-date", time=".event-time", cost=".price, .event-price", age=".age, .event-age", link=".event-title"),
    CardSelectors(card=".event-card", name=".title", date=".date", time=".time", cost=".price", age=".age", link=".title"),
    CardSelectors(card=".event-item", name=".title", date=".date", time=".time", cost=".price", link="a"),
    CardSelectors(card="article", name="h2, h3, .title", date="time, .date", time=".time", link="a"),
]

FULL_DATE_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"\d{1,2},\s+\d{4}\b",
    re.I,
)
TIME_RANGE_RE = re.compile(
    r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM)"
    r"(?:\s*[-–]\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM))?\b",
    re.I,
)
AGE_RE = re.compile(r"(?<!\d)(?:18|21)\+(?!\d)|\bAll Ages\b", re.I)


def _smallest_dated_container(node):
    current = node
    best = node
    for _ in range(7):
        if current is None:
            break
        text = current.get_text(" ", strip=True)
        matches = FULL_DATE_RE.findall(text)
        if matches:
            best = current
            if len(matches) == 1 and len(text) < 900:
                return current
        current = current.parent
    return best


def _parse_insomniac_factory_html(html, source, page_url, year, month):
    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        if "/events/" not in href or "our-world" in href:
            continue

        name = " ".join(anchor.get_text(" ", strip=True).split())
        if not name or name.lower() in {"events", "all events", "buy tickets", "join waitlist"}:
            continue

        context = _smallest_dated_container(anchor)
        text = " ".join(context.get_text(" ", strip=True).split())
        date_match = FULL_DATE_RE.search(text)
        if not date_match:
            continue

        time_match = TIME_RANGE_RE.search(text[date_match.end():])
        time_text = time_match.group(0).upper() if time_match else ""
        start = parse_datetime(f"{date_match.group(0)} {time_text.split('-')[0].strip()}".strip())
        if start is None or start.year != year or start.month != month:
            continue

        age_match = AGE_RE.search(text[:date_match.start()] + " " + text[date_match.end():])
        ticket = None
        for ticket_link in context.find_all("a", href=True):
            ticket_href = str(ticket_link.get("href") or "")
            if "dice.fm" in ticket_href:
                ticket = ticket_href
                break

        lower = text.lower()
        if "festival" in lower:
            category = "Festival / Electronic"
        elif "club" in lower:
            category = "Nightlife / Club"
        else:
            category = "Concert / Electronic"

        cost = "Waitlist" if "waitlist" in lower else "Ticketed"
        event = normalize_event(
            {
                "name": name,
                "start": start.isoformat(),
                "time": time_text or "TBD",
                "venue": source.get("default_venue", "Factory Town"),
                "city": source.get("default_city", "Miami"),
                "category": category,
                "cost": cost,
                "url": ticket or urljoin(page_url, href),
                "source": source.get("name", "Factory Town / Insomniac"),
                "age": age_match.group(0) if age_match else "",
            },
            source,
            page_url,
        )
        if not event:
            continue
        key = (event["date"], event["name"].casefold(), event["venue"].casefold())
        if key not in seen:
            seen.add(key)
            events.append(event)

    return events


def parse_nightlife_html(adapter, html, source, page_url, year, month):
    if adapter == "insomniac_factory":
        return _parse_insomniac_factory_html(html, source, page_url, year, month)

    events = parse_jsonld_html(html, source, page_url, year, month)
    if events:
        return events
    local_source = dict(source)
    local_source.setdefault("default_category", "Nightlife / Party")
    for selectors in PROFILES:
        parsed = parse_event_cards(html, local_source, page_url, selectors, year, month)
        if parsed:
            return parsed
    return []


def collect_nightlife(source, year, month, client=None):
    client = client or HttpClient()
    try:
        response = client.get(source["url"])
        events = parse_nightlife_html(source.get("collector", ""), response.text, source, source["url"], year, month)
        if events or not source.get("browser_fallback"):
            return CollectorResult(events=events, status="ok")
    except Exception as exc:
        if not source.get("browser_fallback"):
            return CollectorResult(status="http_error", message=str(exc))

    try:
        rendered = render_html(source["url"], source.get("wait_selector"))
        events = parse_nightlife_html(source.get("collector", ""), rendered, source, source["url"], year, month)
        return CollectorResult(events=events, status="ok")
    except Exception as exc:
        return CollectorResult(status="browser_error", message=str(exc))
