from pathlib import Path
import scripts.collectors.nightlife as nightlife


def test_zeyzey_fixture_finds_multiple_events():
    html = Path("tests/fixtures/nightlife/zeyzey.html").read_text()
    source = {"name": "ZeyZey", "default_city": "Little River"}
    events = nightlife.parse_nightlife_html("zeyzey", html, source, "https://calendar.zeyzeymiami.com/", 2026, 9)
    names = {e["name"] for e in events}
    assert {"Emmit Fenn", "Tonic Walter"} <= names


def test_liv_fixture_finds_event():
    html = Path("tests/fixtures/nightlife/liv.html").read_text()
    source = {"name": "LIV Miami", "default_city": "Miami Beach"}
    events = nightlife.parse_nightlife_html("liv", html, source, "https://www.livnightclub.com/miami/events/", 2026, 9)
    assert any(e["name"] == "Fetty Wap" for e in events)


def test_browser_fallback_used_when_http_empty(monkeypatch):
    class Resp:
        text = "<html></html>"
    class Client:
        def get(self, url): return Resp()
    source = {"name":"LIV Miami","url":"https://example.com","collector":"liv","default_city":"Miami Beach","browser_fallback":True}
    rendered = Path("tests/fixtures/nightlife/liv.html").read_text()
    monkeypatch.setattr(nightlife, "render_html", lambda *args, **kwargs: rendered)
    result = nightlife.collect_nightlife(source, 2026, 9, client=Client())
    assert result.status == "ok"
    assert any(e["name"] == "Fetty Wap" for e in result.events)


def test_insomniac_factory_town_page_finds_kaskade_and_fisher():
    html = '''
    <section id="upcoming-events">
      <article class="event-card">
        <span>Concerts</span><span>18+</span>
        <a class="event-name" href="/events/kaskade-2026-09-18-miami-fl/">Kaskade</a>
        <span>Origin</span>
        <time>Friday, September 18, 2026</time>
        <span>Miami, FL</span>
        <a href="https://dice.fm/event/kaskade">Buy Tickets</a>
      </article>
      <article class="event-card">
        <span>Concerts</span><span>18+</span>
        <a class="event-name" href="/events/fisher-2026-09-26-miami-fl/">Fisher</a>
        <time>Saturday, September 26, 2026</time>
        <span>Miami, FL</span>
        <a href="https://link.dice.fm/fisher">Join Waitlist</a>
      </article>
    </section>
    '''
    source = {
        "name": "Factory Town / Insomniac",
        "default_city": "Miami",
        "default_venue": "Factory Town",
    }
    events = nightlife.parse_nightlife_html(
        "insomniac_factory", html, source,
        "https://www.insomniac.com/events/our-world/factory-town/", 2026, 9,
    )
    by_name = {event["name"]: event for event in events}
    assert set(by_name) == {"Kaskade", "Fisher"}
    assert by_name["Kaskade"]["date"] == "2026-09-18"
    assert by_name["Kaskade"]["venue"] == "Factory Town"
    assert by_name["Kaskade"]["age"] == "18+"
    assert by_name["Kaskade"]["url"] == "https://dice.fm/event/kaskade"
    assert by_name["Fisher"]["date"] == "2026-09-26"
