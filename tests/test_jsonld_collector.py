from pathlib import Path

from scripts.collectors.jsonld import parse_jsonld_html


def test_jsonld_fixture_extracts_event():
    html = Path("tests/fixtures/jsonld/basic_events.html").read_text(encoding="utf-8")
    source = {
        "name": "Test Arena",
        "url": "https://example.com/events",
        "county": "broward",
        "default_city": "Sunrise",
    }

    events = parse_jsonld_html(
        html,
        source,
        "https://example.com/events",
        2026,
        9,
    )

    assert len(events) == 1
    assert events[0]["name"] == "September Test Concert"
    assert events[0]["venue"] == "Test Arena"
    assert events[0]["date"] == "2026-09-12"
    assert events[0]["cost"] == "USD 35.00"
    assert events[0]["url"] == "https://example.com/tickets/september-test-concert"
