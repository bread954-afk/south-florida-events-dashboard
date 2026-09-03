from dataclasses import dataclass
from bs4 import BeautifulSoup

from scripts.events.normalize import normalize_event, parse_datetime


@dataclass(frozen=True)
class CardSelectors:
    card: str
    name: str
    date: str
    time: str | None = None
    venue: str | None = None
    city: str | None = None
    cost: str | None = None
    age: str | None = None
    link: str | None = None
    category: str | None = None


def _text(card, selector: str | None) -> str:
    if not selector:
        return ""
    node = card.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""


def parse_event_cards(html, source, page_url, selectors, target_year, target_month):
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for card in soup.select(selectors.card):
        date_text = _text(card, selectors.date)
        time_text = _text(card, selectors.time)
        start = parse_datetime(f"{date_text} {time_text}".strip())
        if start is None or start.year != target_year or start.month != target_month:
            continue
        link_node = card.select_one(selectors.link) if selectors.link else None
        raw = {
            "name": _text(card, selectors.name),
            "start": start.isoformat(),
            "time": time_text or None,
            "venue": _text(card, selectors.venue),
            "city": _text(card, selectors.city),
            "cost": _text(card, selectors.cost) or "Check source",
            "age": _text(card, selectors.age),
            "category": _text(card, selectors.category) or source.get("default_category", "Event"),
            "url": link_node.get("href") if link_node and link_node.get("href") else page_url,
        }
        event = normalize_event(raw, source, page_url)
        if event:
            events.append(event)
    return events
