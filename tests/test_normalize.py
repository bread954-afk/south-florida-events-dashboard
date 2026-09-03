from scripts.events.normalize import normalize_event


def test_normalize_event_keeps_existing_schema():
    raw = {
        "name": "September Test Concert",
        "start": "2026-09-12T20:00:00-04:00",
        "venue": "Test Arena",
        "city": "Sunrise",
        "category": "Concert / Music",
        "cost": "$35",
        "url": "/tickets/test",
        "age": "All Ages",
    }
    source = {"name": "Test Arena", "default_city": "Sunrise"}

    event = normalize_event(raw, source, "https://example.com/events")

    assert event == {
        "date": "2026-09-12",
        "time": "8:00 PM",
        "name": "September Test Concert",
        "venue": "Test Arena",
        "city": "Sunrise",
        "category": "Concert / Music",
        "cost": "$35",
        "url": "https://example.com/tickets/test",
        "source": "Test Arena",
        "age": "All Ages",
        "featured": False,
        "new": True,
    }


def test_normalize_rejects_missing_name_or_date():
    source = {"name": "Test", "default_city": "Miami"}
    assert normalize_event({"start": "2026-09-01"}, source, "https://x.test") is None
    assert normalize_event({"name": "No Date"}, source, "https://x.test") is None
