from scripts.collectors.comedy_music import parse_comedy_music_html


def test_miami_improv_preserves_multiple_showtimes():
    html = '''
    <div class="event-card"><a class="event-title" href="/michael-blackson">Michael Blackson</a><span class="event-date">September 4, 2026</span><span class="event-time">7:30 PM</span></div>
    <div class="event-card"><a class="event-title" href="/michael-blackson-late">Michael Blackson</a><span class="event-date">September 4, 2026</span><span class="event-time">10:00 PM</span></div>
    '''
    source = {"name": "Miami Improv", "default_city": "Doral"}
    events = parse_comedy_music_html("miami_improv", html, source, "https://www.miamiimprov.com/events", 2026, 9)
    assert len(events) == 2
    assert {e["time"] for e in events} == {"7:30 PM", "10:00 PM"}
    assert all(e["category"] == "Comedy" for e in events)


def test_revolution_live_parses_concert_card():
    html = '''
    <article class="event-item"><a href="/events/yg"><h3>YG — The Gentlemen's Club Tour</h3></a><time>September 18, 2026 7:00 PM</time></article>
    '''
    source = {"name": "Revolution Live", "default_city": "Fort Lauderdale"}
    events = parse_comedy_music_html("revolution_live", html, source, "https://www.jointherevolution.net/", 2026, 9)
    assert events[0]["name"].startswith("YG")
    assert events[0]["category"] == "Concert / Music"


def test_gulfstream_uses_event_category():
    html = '''
    <div class="event-card"><a class="title" href="/taste-at-the-track">Taste at the Track — Bourbon & BBQ</a><div class="date">September 19, 2026</div><div class="time">1:00 PM</div></div>
    '''
    source = {"name": "Gulfstream Park", "default_city": "Hallandale Beach"}
    events = parse_comedy_music_html("gulfstream", html, source, "https://www.gulfstreampark.com/events/", 2026, 9)
    assert len(events) == 1
    assert events[0]["category"] == "Entertainment / Racing"
