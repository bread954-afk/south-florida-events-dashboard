from scripts.collectors.platforms import collect_platform, parse_platform_html


def test_disabled_platform_is_skipped():
    source = {
        "name": "Blocked Example", "url": "https://example.com", "county": "miami",
        "collector": "eventbrite", "default_city": "Miami", "enabled": False,
    }
    result = collect_platform(source, 2026, 9)
    assert result.status == "disabled"
    assert result.events == []


def test_generic_platform_card_is_normalized():
    html = '''
    <div class="event-card"><a class="event-title" href="/e/party">Wynwood Rooftop Party</a><span class="event-date">September 20, 2026</span><span class="event-time">4:00 PM</span><span class="event-venue">Rooftop Venue</span><span class="event-price">$25</span></div>
    '''
    source = {"name": "Public Event Platform", "default_city": "Wynwood"}
    events = parse_platform_html("eventbrite", html, source, "https://example.com/events", 2026, 9)
    assert len(events) == 1
    assert events[0]["url"] == "https://example.com/e/party"
    assert events[0]["cost"] == "$25"
