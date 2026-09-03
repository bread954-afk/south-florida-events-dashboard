from scripts.events.validate import validate_dataset, validate_event

VALID = {
    "date": "2026-09-05",
    "time": "8:00 PM",
    "name": "Example",
    "venue": "Arena",
    "city": "Miami",
    "category": "Concert",
    "cost": "Ticketed",
    "url": "https://example.com",
    "source": "Arena",
    "age": "",
    "featured": False,
    "new": True,
}


def test_valid_event():
    assert validate_event(VALID) == []


def test_invalid_date():
    errors = validate_event(dict(VALID, date="09/05/2026"))
    assert any("YYYY-MM-DD" in e for e in errors)


def test_missing_required_field():
    broken = dict(VALID)
    broken.pop("venue")
    errors = validate_event(broken)
    assert any("venue" in e for e in errors)


def test_suspicious_count_drop():
    current = [dict(VALID, name=f"Event {i}") for i in range(30)]
    errors = validate_dataset(current, previous_count=130)
    assert any("suspicious count drop" in e for e in errors)
