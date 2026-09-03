from pathlib import Path
from scripts.collectors.arenas import parse_arena_html


def src(name, city):
    return {"name": name, "default_city": city}


def test_hardrock_fixture_finds_known_event():
    html = Path("tests/fixtures/arenas/hardrock_hollywood.html").read_text()
    events = parse_arena_html("hardrock_hollywood", html, src("Seminole Hard Rock Hollywood", "Hollywood"), "https://casino.hardrock.com/hollywood/events/", 2026, 9)
    assert any(e["name"] == "Jo Koy" for e in events)


def test_kaseya_fixture_finds_known_event():
    html = Path("tests/fixtures/arenas/kaseya.html").read_text()
    events = parse_arena_html("kaseya", html, src("Kaseya Center", "Downtown Miami"), "https://www.kaseyacenter.com/events/all", 2026, 9)
    assert any(e["name"] == "Juanes — World Tour 2026" for e in events)


def test_amerant_fixture_finds_known_event():
    html = Path("tests/fixtures/arenas/amerant.html").read_text()
    events = parse_arena_html("amerant", html, src("Amerant Bank Arena", "Sunrise"), "https://www.amerantbankarena.com/events/all", 2026, 9)
    assert any("Fall Fest" in e["name"] for e in events)
