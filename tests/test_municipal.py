from scripts.collectors.municipal import parse_municipal_html


def test_hollywood_calendar_parses_free_event():
    html = '''
    <div class="calendar-item"><a class="title" href="/movie">ArtsPark Movie Night</a><span class="date">September 11, 2026</span><span class="time">8:00 PM</span><span class="cost">Free</span></div>
    '''
    source = {"name": "City of Hollywood", "default_city": "Hollywood"}
    events = parse_municipal_html("hollywood_calendar", html, source, "https://www.hollywoodfl.org/calendar.aspx", 2026, 9)
    assert events[0]["name"] == "ArtsPark Movie Night"
    assert events[0]["cost"] == "Free"
    assert events[0]["category"] == "Community / Event"


def test_doral_calendar_parses_heritage_event():
    html = '''
    <article class="event-card"><a class="event-title" href="/hispanic">Hispanic Heritage Celebration in the Park</a><div class="event-date">September 12, 2026</div><div class="event-time">6:00 PM</div></article>
    '''
    source = {"name": "City of Doral", "default_city": "Doral"}
    events = parse_municipal_html("doral_calendar", html, source, "https://www.cityofdoral.com/events", 2026, 9)
    assert len(events) == 1
    assert events[0]["city"] == "Doral"


def test_miami_worldcenter_night_market():
    html = '''
    <div class="event-item"><a href="/night-market" class="title">Miami Worldcenter Night Market</a><span class="date">September 18, 2026</span><span class="time">5:00 PM</span><span class="price">Free</span></div>
    '''
    source = {"name": "Miami Worldcenter", "default_city": "Downtown Miami"}
    events = parse_municipal_html("miami_worldcenter", html, source, "https://miamiworldcenter.com/events/", 2026, 9)
    assert events[0]["name"] == "Miami Worldcenter Night Market"
