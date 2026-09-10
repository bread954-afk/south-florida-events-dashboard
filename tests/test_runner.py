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


def test_write_last_updated_creates_eastern_timestamp(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import json
    import scripts.update_events as runner

    stamp = datetime(2026, 9, 3, 16, 30, tzinfo=ZoneInfo("America/New_York"))
    payload = runner.write_last_updated(tmp_path, now=stamp)

    saved = json.loads((tmp_path / "last-updated.json").read_text(encoding="utf-8"))
    assert payload == saved
    assert saved == {"updated_at": "2026-09-03T16:30:00-04:00"}


def test_expected_nonempty_source_reports_warning_when_zero_events(tmp_path, monkeypatch):
    path = tmp_path / "miami-events.json"
    path.write_text(json.dumps([EVENT]), encoding="utf-8")

    monkeypatch.setattr(
        runner,
        "collect_source",
        lambda *args, **kwargs: CollectorResult(events=[], status="ok"),
        raising=False,
    )

    before, after, warnings = runner.update_county(
        "miami",
        [{
            "name": "Shotgun Miami",
            "url": "https://example.com",
            "county": "miami",
            "collector": "shotgun",
            "default_city": "Miami",
            "warn_on_empty": True,
        }],
        2026,
        9,
        tmp_path,
    )

    assert (before, after) == (1, 1)
    assert warnings == ["Miami 2026-09 / Shotgun Miami: ok but returned 0 events"]

from datetime import datetime
from zoneinfo import ZoneInfo


def eastern_stamp(year, month, day=10):
    return datetime(year, month, day, 9, 0, tzinfo=ZoneInfo("America/New_York"))


def test_tracked_months_scan_current_plus_future_through_december():
    assert runner.tracked_months(eastern_stamp(2026, 9)) == [
        (2026, 9), (2026, 10), (2026, 11), (2026, 12)
    ]
    assert runner.tracked_months(eastern_stamp(2026, 10)) == [
        (2026, 10), (2026, 11), (2026, 12)
    ]
    assert runner.tracked_months(eastern_stamp(2026, 11)) == [
        (2026, 11), (2026, 12)
    ]
    assert runner.tracked_months(eastern_stamp(2026, 12)) == [(2026, 12)]


def test_tracked_months_clamp_before_window_and_stop_after_2026():
    assert runner.tracked_months(eastern_stamp(2026, 8)) == [
        (2026, 9), (2026, 10), (2026, 11), (2026, 12)
    ]
    assert runner.tracked_months(eastern_stamp(2027, 1)) == []


def event_on(date, name):
    return dict(EVENT, date=date, name=name, url=f"https://example.com/{name.lower().replace(' ', '-')}")


def test_multi_month_county_run_collects_each_month_and_writes_once(tmp_path, monkeypatch):
    path = tmp_path / "miami-events.json"
    september = event_on("2026-09-05", "September Existing")
    path.write_text(json.dumps([september]), encoding="utf-8")
    calls = []

    def fake_collect(source, year, month):
        calls.append((source["name"], year, month))
        return CollectorResult(
            events=[event_on(f"2026-{month:02d}-15", f"Month {month} Event")],
            status="ok",
        )

    monkeypatch.setattr(runner, "collect_source", fake_collect)
    before, after, warnings = runner.update_county_months(
        "miami",
        [{
            "name": "Test Source", "url": "https://example.com/events",
            "county": "miami", "collector": "jsonld", "default_city": "Miami",
        }],
        [(2026, 10), (2026, 11), (2026, 12)],
        tmp_path,
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert calls == [
        ("Test Source", 2026, 10),
        ("Test Source", 2026, 11),
        ("Test Source", 2026, 12),
    ]
    assert before == 1
    assert after == 4
    assert warnings == []
    assert september in saved
    assert {e["date"][:7] for e in saved} == {"2026-09", "2026-10", "2026-11", "2026-12"}


def test_one_month_failure_does_not_block_later_months(tmp_path, monkeypatch):
    path = tmp_path / "broward-events.json"
    path.write_text("[]", encoding="utf-8")

    def fake_collect(source, year, month):
        if month == 10:
            return CollectorResult(events=[], status="http_error", message="offline")
        return CollectorResult(
            events=[event_on(f"2026-{month:02d}-20", f"Broward {month}")],
            status="ok",
        )

    monkeypatch.setattr(runner, "collect_source", fake_collect)
    before, after, warnings = runner.update_county_months(
        "broward",
        [{
            "name": "Test Source", "url": "https://example.com/events",
            "county": "broward", "collector": "jsonld", "default_city": "Hollywood",
        }],
        [(2026, 10), (2026, 11), (2026, 12)],
        tmp_path,
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert (before, after) == (0, 2)
    assert {e["date"] for e in saved} == {"2026-11-20", "2026-12-20"}
    assert warnings == ["Broward 2026-10 / Test Source: http_error: offline"]


def test_warn_on_empty_includes_county_and_month_context(tmp_path, monkeypatch):
    path = tmp_path / "miami-events.json"
    path.write_text(json.dumps([EVENT]), encoding="utf-8")
    monkeypatch.setattr(
        runner,
        "collect_source",
        lambda *args, **kwargs: CollectorResult(events=[], status="ok"),
    )

    _, _, warnings = runner.update_county_months(
        "miami",
        [{
            "name": "Shotgun Miami", "url": "https://example.com",
            "county": "miami", "collector": "shotgun", "default_city": "Miami",
            "warn_on_empty": True,
        }],
        [(2026, 11)],
        tmp_path,
    )

    assert warnings == ["Miami 2026-11 / Shotgun Miami: ok but returned 0 events"]


def test_main_writes_last_updated_once(tmp_path, monkeypatch):
    (tmp_path / "sources.json").write_text(
        json.dumps({"broward": [], "miami": []}), encoding="utf-8"
    )
    calls = []

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "current_eastern_time", lambda: eastern_stamp(2026, 9))
    monkeypatch.setattr(
        runner,
        "write_last_updated",
        lambda root, now=None: calls.append((root, now)) or {"updated_at": "2026-09-10T09:00:00-04:00"},
    )

    assert runner.main() == 0
    assert len(calls) == 1
