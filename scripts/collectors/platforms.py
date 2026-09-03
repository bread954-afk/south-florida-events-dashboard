from scripts.collectors.base import CollectorResult, HttpClient
from scripts.collectors.browser import render_html
from scripts.collectors.html_cards import CardSelectors, parse_event_cards
from scripts.collectors.jsonld import parse_jsonld_html

PROFILES = [
    CardSelectors(card='.event-card', name='.event-title, .title', date='.event-date, .date', time='.event-time, .time', venue='.event-venue, .venue', cost='.event-price, .price', link='a'),
    CardSelectors(card='.search-event-card-wrapper, .discover-search-desktop-card', name='h2, h3, .event-title', date='time, .date', venue='.venue, .event-venue', cost='.price, .event-price', link='a'),
    CardSelectors(card='article', name='h2, h3, .title', date='time, .date', time='.time', venue='.venue', cost='.price', link='a'),
]


def parse_platform_html(adapter, html, source, page_url, year, month):
    local_source = dict(source)
    local_source['default_category'] = 'Event'

    events = parse_jsonld_html(html, local_source, page_url, year, month)
    if events:
        return events
    for selectors in PROFILES:
        parsed = parse_event_cards(html, local_source, page_url, selectors, year, month)
        if parsed:
            return parsed
    return []


def collect_platform(source, year, month, client=None):
    if source.get('enabled', True) is False:
        return CollectorResult(status='disabled', message='source disabled')

    client = client or HttpClient()
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
