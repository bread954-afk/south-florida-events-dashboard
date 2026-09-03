import json

import scripts.update_events as runner
from scripts.collectors.base import CollectorResult


EVENT = {
    "date": "2026-09-05",
    "time": "8:00 PM",
    "name": "Existing Event",
    "venue": "Existing Venue",
    "city": "Miami",
    "category": "Event",
    "cost": "Check source",
    "url": "https://example.com",
    "source": "Existing Venue",
    "age": "",
    "featured": False,
    "new": True,
}


def test_existing_event_schema():
    assert set(EVENT) == {
        "date", "time", "name", "venue", "city", "category",
        "cost", "url", "source", "age", "featured", "new"
    }


def test_failed_source_does_not_remove_existing(tmp_path, monkeypatch):
    path = tmp_path / "miami-events.json"
    path.write_text(json.dumps([EVENT]), encoding="utf-8")

    monkeypatch.setattr(
        runner,
        "collect_source",
        lambda *args, **kwargs: CollectorResult(
            events=[], status="http_error", message="offline"
        ),
        raising=False,
    )

    before, after, warnings = runner.update_county(
        "miami",
        [{
            "name": "Broken",
            "url": "https://example.com",
            "county": "miami",
            "collector": "jsonld",
            "default_city": "Miami",
        }],
        2026,
        9,
        tmp_path,
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert before == 1
    assert after == 1
    assert saved == [EVENT]
    assert warnings


def test_new_event_is_appended(tmp_path, monkeypatch):
    path = tmp_path / "broward-events.json"
    path.write_text("[]", encoding="utf-8")
    new_event = dict(EVENT, city="Hollywood", venue="Hard Rock Live")

    monkeypatch.setattr(
        runner,
        "collect_source",
        lambda *args, **kwargs: CollectorResult(events=[new_event], status="ok"),
        raising=False,
    )

    before, after, warnings = runner.update_county(
        "broward",
        [{
            "name": "Hard Rock",
            "url": "https://example.com",
            "county": "broward",
            "collector": "jsonld",
            "default_city": "Hollywood",
        }],
        2026,
        9,
        tmp_path,
    )

    assert (before, after) == (0, 1)
    assert warnings == []


def test_disabled_source_is_skipped_without_warning(tmp_path, monkeypatch):
    path = tmp_path / "miami-events.json"
    path.write_text(json.dumps([EVENT]), encoding="utf-8")

    def should_not_run(*args, **kwargs):
        raise AssertionError("disabled source should not be collected")

    monkeypatch.setattr(runner, "collect_source", should_not_run, raising=False)

    before, after, warnings = runner.update_county(
        "miami",
        [{
            "name": "Disabled",
            "url": "https://example.com",
            "county": "miami",
            "collector": "jsonld",
            "default_city": "Miami",
            "enabled": False,
        }],
        2026,
        9,
        tmp_path,
    )

    assert (before, after) == (1, 1)
    assert warnings == []


def test_invalid_merged_dataset_is_not_written(tmp_path, monkeypatch):
    path = tmp_path / "broward-events.json"
    path.write_text(json.dumps([EVENT]), encoding="utf-8")
    bad = dict(EVENT, date="not-a-date", name="Broken Event")

    monkeypatch.setattr(
        runner,
        "collect_source",
        lambda *args, **kwargs: CollectorResult(events=[bad], status="ok"),
        raising=False,
    )

    try:
        runner.update_county(
            "broward",
            [{
                "name": "Bad",
                "url": "https://example.com",
                "county": "broward",
                "collector": "jsonld",
                "default_city": "Hollywood",
            }],
            2026,
            9,
            tmp_path,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == [EVENT]
