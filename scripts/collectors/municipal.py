from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html

PROFILES = [
    CardSelectors(card='.calendar-item', name='.title, .event-title', date='.date, .event-date', time='.time, .event-time', cost='.cost, .price', link='a'),
    CardSelectors(card='.event-card', name='.event-title, .title', date='.event-date, .date', time='.event-time, .time', cost='.event-price, .cost, .price', link='a'),
    CardSelectors(card='.event-item', name='.title, h2, h3', date='.date, time', time='.time', cost='.price, .cost', link='a'),
    CardSelectors(card='article', name='h2, h3, .title', date='time, .date', time='.time', cost='.price, .cost', link='a'),
]


def parse_municipal_html(adapter, html, source, page_url, year, month):
    local_source = dict(source)
    local_source['default_category'] = 'Community / Event'

    events = parse_jsonld_html(html, local_source, page_url, year, month)
    if events:
        for event in events:
            if event.get('category') == 'Event':
                event['category'] = 'Community / Event'
        return events

    for selectors in PROFILES:
        parsed = parse_event_cards(html, local_source, page_url, selectors, year, month)
        if parsed:
            return parsed
    return []


def collect_municipal(source, year, month, client=None):
    client = client or HttpClient()
    try:
        response = client.get(source['url'])
        events = parse_municipal_html(
            source.get('collector', ''), response.text, source, source['url'], year, month
        )
        return CollectorResult(events=events, status='ok')
    except Exception as exc:
        return CollectorResult(status='parser_error', message=str(exc))
