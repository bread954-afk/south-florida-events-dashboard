from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html

PROFILES = [
    CardSelectors(card='.event-card', name='.event-title', date='.event-date', time='.event-time', cost='.event-price, .price', age='.event-age, .age', link='.event-title'),
    CardSelectors(card='.event-card', name='.title', date='.date', time='.time', cost='.price', age='.age', link='.title'),
    CardSelectors(card='.event-item', name='h3, .title', date='time, .date', time='.time', cost='.price', link='a'),
    CardSelectors(card='article', name='h2, h3, .title', date='time, .date', time='.time', cost='.price', link='a'),
]

DEFAULT_CATEGORIES = {
    'miami_improv': 'Comedy',
    'dania_improv': 'Comedy',
    'revolution_live': 'Concert / Music',
    'culture_room': 'Concert / Music',
    'gulfstream': 'Entertainment / Racing',
}


def parse_comedy_music_html(adapter, html, source, page_url, year, month):
    local_source = dict(source)
    local_source['default_category'] = DEFAULT_CATEGORIES.get(adapter, 'Entertainment')

    events = parse_jsonld_html(html, local_source, page_url, year, month)
    if events:
        for event in events:
            if event.get('category') == 'Event':
                event['category'] = local_source['default_category']
        return events

    for selectors in PROFILES:
        parsed = parse_event_cards(html, local_source, page_url, selectors, year, month)
        if parsed:
            return parsed
    return []


def collect_comedy_music(source, year, month, client=None):
    client = client or HttpClient()
    try:
        response = client.get(source['url'])
        events = parse_comedy_music_html(
            source.get('collector', ''), response.text, source, source['url'], year, month
        )
        return CollectorResult(events=events, status='ok')
    except Exception as exc:
        return CollectorResult(status='parser_error', message=str(exc))
