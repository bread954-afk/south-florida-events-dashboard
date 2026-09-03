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
