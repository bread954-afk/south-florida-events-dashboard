import json
from pathlib import Path

from scripts.collectors.router import collector_name, validate_source


def test_registry_requires_url_and_county():
    errors = validate_source({"name": "ZeyZey"})
    assert any("url" in e for e in errors)
    assert any("county" in e for e in errors)


def test_explicit_adapter_wins():
    source = {
        "name": "ZeyZey",
        "url": "https://calendar.zeyzeymiami.com/",
        "county": "miami",
        "collector": "zeyzey",
        "default_city": "Little River",
        "browser_fallback": False,
    }
    assert collector_name(source) == "zeyzey"


def test_default_collector_is_jsonld():
    source = {
        "name": "Example",
        "url": "https://example.com/events",
        "county": "broward",
        "default_city": "Hollywood",
    }
    assert collector_name(source) == "jsonld"


def test_all_sources_have_valid_registry_shape():
    data = json.loads(Path("sources.json").read_text(encoding="utf-8"))
    errors = []
    for county, sources in data.items():
        for source in sources:
            errors.extend(
                f"{county}/{source.get('name')}: {error}"
                for error in validate_source(source)
            )
            assert source["county"] == county
    assert errors == []


def test_arena_collector_group_routes_to_arena():
    from scripts.collectors.router import collector_group
    assert collector_group("kaseya") == "arena"
    assert collector_group("amerant") == "arena"


def test_nightlife_collector_group_routes_to_nightlife():
    from scripts.collectors.router import collector_group
    assert collector_group("liv") == "nightlife"
    assert collector_group("zeyzey") == "nightlife"
