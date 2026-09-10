import re
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.browser import render_html
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html
from scripts.events.normalize import normalize_event, parse_datetime


PROFILES = [
    CardSelectors(card='.event-card', name='.event-title, .title', date='.event-date, .date', time='.event-time, .time', venue='.event-venue, .venue', cost='.event-price, .price', link='a'),
    CardSelectors(card='.search-event-card-wrapper, .discover-search-desktop-card', name='h2, h3, .event-title', date='time, .date', venue='.venue, .event-venue', cost='.price, .event-price', link='a'),
    CardSelectors(card='article', name='h2, h3, .title', date='time, .date', time='.time', venue='.venue', cost='.price', link='a'),
]

SHOTGUN_DATE_RE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+"
    r"\d{1,2}(?:,\s*\d{4})?\b",
    re.I,
)
TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b", re.I)
PRICE_RE = re.compile(r"\$\s*\d+(?:\.\d{1,2})?")
AGE_RE = re.compile(r"(?<!\d)(?:18|21)\+(?!\d)|\bAll Ages\b", re.I)
STATUS_COSTS = ("Free", "Sold out", "Waiting list", "Pre-registration", "Waitlist")


def _node_strings(node) -> list[str]:
    values = []
    for text in node.stripped_strings:
        value = " ".join(str(text).split())
        if value and (not values or value != values[-1]):
            values.append(value)
    return values


def _smallest_context_with_date(node, pattern, max_levels=7):
    current = node
    for _ in range(max_levels):
        if current is None:
            break
        text = current.get_text(" ", strip=True)
        if pattern.search(text):
            return current
        current = current.parent
    return node


def _class_text(node, selectors: str) -> str:
    match = node.select_one(selectors)
    return match.get_text(" ", strip=True) if match else ""


def _partial_date(date_text: str, year: int, time_text: str = ""):
    dated = date_text if re.search(r"\b\d{4}\b", date_text) else f"{date_text}, {year}"
    return parse_datetime(f"{dated} {time_text}".strip())


def _shotgun_name_venue(context, anchor, date_text: str) -> tuple[str, str]:
    name = _class_text(
        context,
        ".event-name, .event-title, [class*='event-name'], [class*='event-title']",
    )
    venue = _class_text(
        context,
        ".event-venue, .venue, [class*='event-venue'], [class*='venue'], [class*='location']",
    )

    strings = _node_strings(context)
    date_index = next(
        (i for i, value in enumerate(strings) if SHOTGUN_DATE_RE.search(value)),
        None,
    )
    prefix = strings[:date_index] if date_index is not None else []

    anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
    if not name:
        if anchor_text and not SHOTGUN_DATE_RE.search(anchor_text) and len(anchor_text) <= 220:
            name = anchor_text
        elif prefix:
            name = prefix[0]

    if not venue and prefix:
        remainder = [value for value in prefix if value != name]
        if remainder:
            venue = remainder[-1]

    return name.strip(), venue.strip()


def parse_shotgun_html(html, source, page_url, year, month):
    """Parse Shotgun's public city/event cards without requiring private APIs."""
    local_source = dict(source)
    local_source.setdefault("default_category", "Nightlife / Event")

    jsonld = parse_jsonld_html(html, local_source, page_url, year, month)
    if jsonld:
        return jsonld

    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        if "/events/" not in href:
            continue

        context = _smallest_context_with_date(anchor, SHOTGUN_DATE_RE)
        text = " ".join(context.get_text(" ", strip=True).split())
        date_match = SHOTGUN_DATE_RE.search(text)
        if not date_match:
            continue

        date_text = date_match.group(0)
        time_match = TIME_RE.search(text[date_match.end():]) or TIME_RE.search(text)
        time_text = time_match.group(0).upper() if time_match else ""
        start = _partial_date(date_text, year, time_text)
        if start is None or start.year != year or start.month != month:
            continue

        name, venue = _shotgun_name_venue(context, anchor, date_text)
        if not name:
            continue

        cost_match = PRICE_RE.search(text)
        if cost_match:
            cost = cost_match.group(0).replace(" ", "")
        else:
            cost = next((label for label in STATUS_COSTS if label.lower() in text.lower()), "Check source")

        age_match = AGE_RE.search(text)
        raw = {
            "name": name,
            "start": start.isoformat(),
            "time": time_text or "TBD",
            "venue": venue or source.get("default_venue") or source.get("default_city", "Miami"),
            "city": source.get("default_city", "Miami"),
            "category": source.get("default_category", "Nightlife / Event"),
            "cost": cost,
            "age": age_match.group(0) if age_match else "",
            "url": urljoin(page_url, href),
            "source": source.get("name", "Shotgun"),
        }
        event = normalize_event(raw, local_source, page_url)
        if not event:
            continue

        key = (event["date"], event["name"].casefold(), event["venue"].casefold())
        if key not in seen:
            seen.add(key)
            events.append(event)

    return events


def parse_platform_html(adapter, html, source, page_url, year, month):
    local_source = dict(source)
    local_source['default_category'] = source.get('default_category', 'Event')

    if adapter == "shotgun":
        return parse_shotgun_html(html, local_source, page_url, year, month)

    events = parse_jsonld_html(html, local_source, page_url, year, month)
    if events:
        return events
    for selectors in PROFILES:
        parsed = parse_event_cards(html, local_source, page_url, selectors, year, month)
        if parsed:
            return parsed
    return []


def _with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["page"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _collect_shotgun(source, year, month, client):
    events = []
    max_pages = max(1, int(source.get("max_pages", 1)))

    for page in range(1, max_pages + 1):
        page_url = _with_page(source["url"], page)
        response = client.get(page_url)
        parsed = parse_shotgun_html(response.text, source, page_url, year, month)
        if not parsed:
            break
        events.extend(parsed)

    unique = {}
    for event in events:
        key = (event["date"], event["name"].casefold(), event["venue"].casefold())
        unique[key] = event
    return list(unique.values())


def collect_platform(source, year, month, client=None):
    if source.get('enabled', True) is False:
        return CollectorResult(status='disabled', message='source disabled')

    client = client or HttpClient()

    if source.get("collector") == "shotgun":
        try:
            events = _collect_shotgun(source, year, month, client)
            return CollectorResult(events=events, status="ok")
        except Exception as exc:
            return CollectorResult(status="http_error", message=str(exc))

    http_error = None
    try:
        response = client.get(source['url'])
        events = parse_platform_html(
            source.get('collector', ''), response.text, source, source['url'], year, month
        )
        if events or not source.get('browser_fallback'):
            return CollectorResult(events=events, status='ok')
    except Exception as exc:
        http_error = exc
        if not source.get('browser_fallback'):
            status = 'blocked' if '403' in str(exc) or '429' in str(exc) else 'http_error'
            return CollectorResult(status=status, message=str(exc))

    try:
        rendered = render_html(source['url'], source.get('wait_selector'))
        events = parse_platform_html(
            source.get('collector', ''), rendered, source, source['url'], year, month
        )
        return CollectorResult(events=events, status='ok')
    except Exception as exc:
        message = str(exc) if http_error is None else f'http={http_error}; browser={exc}'
        return CollectorResult(status='browser_error', message=message)
