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


def test_same_start_time_with_range_dedupes():
    merged = merge_events(
        [event(name="Kaskade", venue="Factory Town", time="10:00 PM")],
        [event(name="Kaskade", venue="Factory Town", time="10:00 PM - 5:00 AM", cost="$45+")],
    )
    assert len(merged) == 1
    assert merged[0]["cost"] == "$45+"


def test_equivalent_time_format_dedupes():
    merged = merge_events(
        [event(name="Fisher", venue="Factory Town", time="10 PM")],
        [event(name="Fisher", venue="Factory Town", time="10:00 PM")],
    )
    assert len(merged) == 1


def test_same_event_specific_url_can_update_date_time_and_venue():
    existing = [{
        "date": "2026-09-18", "time": "8:00 PM", "name": "Test Tour",
        "venue": "Old Venue", "city": "Miami", "category": "Concert",
        "cost": "$40", "url": "https://tickets.example.com/events/test-tour?src=old",
        "source": "Official Tickets", "age": "18+", "featured": False, "new": True,
    }]
    discovered = [{
        "date": "2026-10-02", "time": "9:00 PM", "name": "Test Tour",
        "venue": "New Venue", "city": "Miami Beach", "category": "Concert",
        "cost": "$45", "url": "https://tickets.example.com/events/test-tour?src=new",
        "source": "Official Tickets", "age": "18+", "featured": True, "new": True,
    }]

    merged = merge_events(existing, discovered)
    assert len(merged) == 1
    assert merged[0]["date"] == "2026-10-02"
    assert merged[0]["time"] == "9:00 PM"
    assert merged[0]["venue"] == "New Venue"
    assert merged[0]["city"] == "Miami Beach"
    assert merged[0]["cost"] == "$45"
    assert merged[0]["featured"] is True


def test_cancelled_wording_can_update_same_url_event_name_without_duplicate():
    existing = [{
        "date": "2026-11-10", "time": "7:00 PM", "name": "Example Live",
        "venue": "Example Hall", "city": "Miami", "category": "Concert",
        "cost": "$50", "url": "https://example.com/event/123", "source": "Example Hall",
        "age": "", "featured": False, "new": True,
    }]
    discovered = [{
        **existing[0],
        "name": "CANCELLED — Example Live",
        "cost": "Cancelled / refunds at source",
    }]

    merged = merge_events(existing, discovered)
    assert len(merged) == 1
    assert merged[0]["name"] == "CANCELLED — Example Live"
    assert merged[0]["cost"] == "Cancelled / refunds at source"


def test_reused_generic_url_does_not_collapse_different_events():
    existing = [
        {
            "date": "2026-10-03", "time": "7:00 PM", "name": "Event A",
            "venue": "Venue", "city": "Miami", "category": "Event", "cost": "$10",
            "url": "https://venue.example.com/events", "source": "Venue", "age": "",
            "featured": False, "new": True,
        },
        {
            "date": "2026-10-04", "time": "8:00 PM", "name": "Event B",
            "venue": "Venue", "city": "Miami", "category": "Event", "cost": "$10",
            "url": "https://venue.example.com/events", "source": "Venue", "age": "",
            "featured": False, "new": True,
        },
    ]
    discovered = [{
        **existing[0],
        "date": "2026-10-05",
        "name": "Unrelated Event C",
    }]

    merged = merge_events(existing, discovered)
    assert len(merged) == 3
