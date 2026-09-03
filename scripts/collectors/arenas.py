from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html


COMMON_PROFILES = [
    CardSelectors(card=".event-card", name=".event-title", date=".event-date", time=".event-time", link=".event-title"),
    CardSelectors(card=".event-card", name=".title", date=".date", time=".time", link=".title"),
    CardSelectors(card=".event-item", name=".title", date=".date", time=".time", link=".title"),
    CardSelectors(card="article.event", name="h2, h3, .title", date=".date", time=".time", link="a"),
]

ARENA_ADAPTERS = {
    "hardrock_hollywood", "amerant", "broward_center", "kaseya",
    "hard_rock_stadium", "arsht", "jlkc", "miami_beach_bandshell",
}


def parse_arena_html(adapter, html, source, page_url, year, month):
    events = parse_jsonld_html(html, source, page_url, year, month)
    if events:
        return events
    for selectors in COMMON_PROFILES:
        parsed = parse_event_cards(html, source, page_url, selectors, year, month)
        if parsed:
            return parsed
    return []


def collect_arena(source, year, month, client=None):
    client = client or HttpClient()
    try:
        response = client.get(source["url"])
        events = parse_arena_html(source.get("collector", ""), response.text, source, source["url"], year, month)
        return CollectorResult(events=events, status="ok")
    except Exception as exc:
        return CollectorResult(status="parser_error", message=str(exc))
