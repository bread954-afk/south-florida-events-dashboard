from scripts.events.merge import event_key, merge_events


def event(**changes):
    value = {
        "date": "2026-09-05",
        "time": "8:00 PM",
        "name": "TLC & Salt-N-Pepa",
        "venue": "Hard Rock Live",
        "city": "Hollywood",
        "category": "Concert",
        "cost": "Check source",
        "url": "https://example.com",
        "source": "Hard Rock Live",
        "age": "",
        "featured": True,
        "new": True,
    }
    value.update(changes)
    return value


def test_identity_normalizes_punctuation():
    assert event_key(event(name="TLC & Salt-N-Pepa"))[:3] == \
           event_key(event(name="tlc salt n pepa"))[:3]


def test_matching_event_updates_richer_fields_without_duplicate():
    merged = merge_events(
        [event()],
        [event(cost="$35+", url="https://tickets.example.com")],
    )
    assert len(merged) == 1
    assert merged[0]["cost"] == "$35+"
    assert merged[0]["url"] == "https://tickets.example.com"


def test_multiple_same_day_showtimes_survive():
    merged = merge_events(
        [event(name="Disney On Ice", time="3:00 PM")],
        [event(name="Disney On Ice", time="7:00 PM")],
    )
    assert len(merged) == 2


def test_empty_discovery_never_deletes_existing():
    existing = [event()]
    assert merge_events(existing, []) == existing
