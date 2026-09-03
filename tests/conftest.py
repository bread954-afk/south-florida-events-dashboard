from pathlib import Path
import pytest


@pytest.fixture
def existing_event() -> dict:
    return {
        "date": "2026-09-05",
        "time": "8:00 PM",
        "name": "Example Concert",
        "venue": "Example Arena",
        "city": "Miami",
        "category": "Concert / Music",
        "cost": "Ticketed",
        "url": "https://example.com/event",
        "source": "Example Arena",
        "age": "",
        "featured": False,
        "new": True,
    }
