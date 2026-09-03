from scripts.collectors.html_cards import CardSelectors, parse_event_cards

HTML = '''
<div class="event-card">
  <a class="title" href="/events/jo-koy">Jo Koy</a>
  <div class="date">September 4, 2026</div>
  <div class="time">8:00 PM</div>
  <div class="venue">Hard Rock Live</div>
  <div class="price">Ticketed</div>
</div>
'''


def test_parse_event_cards():
    selectors = CardSelectors(
        card=".event-card",
        name=".title",
        date=".date",
        time=".time",
        venue=".venue",
        cost=".price",
        link=".title",
    )
    source = {"name": "Seminole Hard Rock Hollywood", "default_city": "Hollywood"}
    events = parse_event_cards(
        HTML,
        source,
        "https://example.com/events",
        selectors,
        2026,
        9,
    )
    assert events[0]["name"] == "Jo Koy"
    assert events[0]["date"] == "2026-09-04"
    assert events[0]["time"] == "8:00 PM"
    assert events[0]["url"] == "https://example.com/events/jo-koy"
