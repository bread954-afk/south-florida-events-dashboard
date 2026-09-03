from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.browser import render_html
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html


PROFILES = [
    CardSelectors(card=".event-card", name=".event-title", date=".event-date", time=".event-time", cost=".price, .event-price", age=".age, .event-age", link=".event-title"),
    CardSelectors(card=".event-card", name=".title", date=".date", time=".time", cost=".price", age=".age", link=".title"),
    CardSelectors(card=".event-item", name=".title", date=".date", time=".time", cost=".price", link="a"),
    CardSelectors(card="article", name="h2, h3, .title", date="time, .date", time=".time", link="a"),
]


def parse_nightlife_html(adapter, html, source, page_url, year, month):
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
