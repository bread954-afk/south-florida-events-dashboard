from scripts.collectors.platforms import collect_platform, parse_platform_html, parse_shotgun_html


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


def test_shotgun_city_cards_parse_name_venue_date_time_and_price():
    html = '''
    <main>
      <a class="event-link" href="/en/events/kaytraday-fall-2026-tour-miami-fl">
        <span class="event-name">Kaytraday! Fall 2026 Tour (Miami, Fl)</span>
        <span class="event-venue">ZeyZey Miami</span>
        <span>Fri, Sep 11</span><span>9:00 PM</span><span>$22.70</span>
        <span>Amapiano</span><span>R&amp;B</span><span>Dance</span>
      </a>
      <a class="event-link" href="/en/events/soundtuaryxrasa2">
        <span class="event-name">Soundtuary X Rasa Present &amp;Friends, Apache &amp; Malas</span>
        <span class="event-venue">Jungle Island</span>
        <span>Sat, Sep 12</span><span>8:00 PM</span><span>$28.38</span>
        <span>House</span><span>Afro House</span>
      </a>
      <a class="event-link" href="/en/events/unotheactivist-live-in-miami">
        <span class="event-name">Unotheactivist Live In Miami</span>
        <span class="event-venue">The Boombox Miami</span>
        <span>Sun, Sep 13</span><span>6:00 PM</span><span>$30.00</span>
        <span>Rap</span><span>Hip Hop</span>
      </a>
    </main>
    '''
    source = {
        "name": "Shotgun Miami",
        "default_city": "Miami",
        "default_category": "Nightlife / Event",
    }
    events = parse_shotgun_html(html, source, "https://r.shotgun.live/en/cities/miami", 2026, 9)

    by_name = {event["name"]: event for event in events}
    assert set(by_name) == {
        "Kaytraday! Fall 2026 Tour (Miami, Fl)",
        "Soundtuary X Rasa Present &Friends, Apache & Malas",
        "Unotheactivist Live In Miami",
    }
    assert by_name["Kaytraday! Fall 2026 Tour (Miami, Fl)"]["venue"] == "ZeyZey Miami"
    assert by_name["Kaytraday! Fall 2026 Tour (Miami, Fl)"]["date"] == "2026-09-11"
    assert by_name["Kaytraday! Fall 2026 Tour (Miami, Fl)"]["time"] == "9:00 PM"
    assert by_name["Kaytraday! Fall 2026 Tour (Miami, Fl)"]["cost"] == "$22.70"
    assert by_name["Kaytraday! Fall 2026 Tour (Miami, Fl)"]["url"].endswith(
        "/en/events/kaytraday-fall-2026-tour-miami-fl"
    )


def test_shotgun_collector_paginates_city_pages_and_stops_after_empty_page():
    pages = {
        "https://r.shotgun.live/en/cities/miami?page=1": '''
            <a href="/en/events/kaytraday-fall-2026-tour-miami-fl">
              <span>Kaytraday! Fall 2026 Tour (Miami, Fl)</span><span>ZeyZey Miami</span>
              <span>Fri, Sep 11</span><span>9:00 PM</span><span>$22.70</span>
            </a>
        ''',
        "https://r.shotgun.live/en/cities/miami?page=2": '''
            <a href="/en/events/unotheactivist-live-in-miami">
              <span>Unotheactivist Live In Miami</span><span>The Boombox Miami</span>
              <span>Sun, Sep 13</span><span>6:00 PM</span><span>$30.00</span>
            </a>
        ''',
        "https://r.shotgun.live/en/cities/miami?page=3": "<html><body>No more September events</body></html>",
    }

    class Resp:
        def __init__(self, text):
            self.text = text

    class Client:
        def __init__(self):
            self.urls = []

        def get(self, url):
            self.urls.append(url)
            return Resp(pages[url])

    client = Client()
    source = {
        "name": "Shotgun Miami",
        "url": "https://r.shotgun.live/en/cities/miami",
        "county": "miami",
        "collector": "shotgun",
        "default_city": "Miami",
        "browser_fallback": False,
        "max_pages": 8,
    }
    result = collect_platform(source, 2026, 9, client=client)
    assert result.status == "ok"
    assert {event["name"] for event in result.events} == {
        "Kaytraday! Fall 2026 Tour (Miami, Fl)",
        "Unotheactivist Live In Miami",
    }
    assert client.urls == [
        "https://r.shotgun.live/en/cities/miami?page=1",
        "https://r.shotgun.live/en/cities/miami?page=2",
        "https://r.shotgun.live/en/cities/miami?page=3",
    ]
