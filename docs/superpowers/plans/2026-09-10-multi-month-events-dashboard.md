# Sep–Dec 2026 Multi-Month Events Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the existing Miami-Dade and Broward event dashboards and daily updater from September-only behavior to a single-page Sep–Dec 2026 experience with a month selector, shared favorites, dynamic calendar geometry, and current-plus-future-month discovery.

**Architecture:** Keep `miami-events.json` and `broward-events.json` as county-wide archives and add a small shared browser month/date helper used by both dashboards. Refactor the updater so one county run collects every tracked month into memory, merges once, validates once, and writes once, while retaining source/month failure isolation. Keep the existing static GitHub Pages deployment, event schema, and county-specific favorites keys.

**Tech Stack:** Python 3.12, pytest, requests, BeautifulSoup4, Playwright Chromium, vanilla HTML/CSS/JavaScript, Node.js for pure-JS unit tests, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-10-multi-month-events-dashboard-design.md`

## Global Constraints

- Supported dashboard months are exactly `2026-09`, `2026-10`, `2026-11`, and `2026-12`.
- Keep one Miami-Dade page (`miami.html`) and one Broward page (`broward.html`); do not create per-month pages.
- Default month uses the browser's local date, clamped to September before the supported window and December after it.
- Favorites remain shared across Sep–Dec using the existing county-specific localStorage keys.
- Keep the exact event keys: `date`, `time`, `name`, `venue`, `city`, `category`, `cost`, `url`, `source`, `age`, `featured`, `new`.
- No paid API, paid scraping service, subscription, database, server, secret, or required API key.
- Completed months stay in county JSON and are not rescanned by normal daily runs.
- One failed source or month must not stop other sources or months.
- Failed or empty collection must never delete existing events.
- Validate the complete county dataset before writing it.
- Preserve all current September data and existing GitHub Pages URLs.
- `This week` means the browser-local Sunday-through-Saturday calendar week containing today.
- `This weekend` means the Friday, Saturday, and Sunday weekend whose Friday/Saturday fall in the browser-local Sunday-through-Saturday week containing today.

---

## File Structure

### Create

- `dashboard-months.js` — shared pure functions for supported-month selection, month geometry, event month checks, current-week date keys, and current-weekend date keys. Exposes both `window.SFMonths` and `module.exports` so browsers and Node tests use the same implementation.
- `tests/test_dashboard_months.py` — Node-backed unit tests for `dashboard-months.js`.
- `tests/test_dashboard_multimonth_browser.py` — Playwright browser tests for real month switching, selected-day reset, filter persistence, shared favorites, empty state, and dynamic calendar rendering.

### Modify

- `scripts/update_events.py` — add tracked-month calculation, month-aware collection/logging, merge-once/write-once county orchestration, Eastern-time clock helper, and after-December no-op discovery behavior.
- `scripts/events/merge.py` — allow confident material updates when the same event-specific source URL and normalized event name identify a moved/rescheduled/cancelled event.
- `tests/test_runner.py` — cover Sep–Dec tracking windows, multi-month collection, completed-month preservation, failure isolation, warning context, and single timestamp write.
- `tests/test_merge.py` — cover URL-backed date/venue changes and guard against collapsing unrelated events.
- `miami.html` — add the month selector and replace September-specific filtering/calendar/date labels with shared dynamic behavior.
- `broward.html` — mirror the Miami month behavior while keeping Broward labels/data/favorites key.
- `tests/test_dashboard_features.py` — assert both dashboards load the shared month helper, expose the approved selector options, and keep county-specific favorites keys/mobile controls.
- `README-AUTO-UPDATE.md` — document multi-month scan behavior, month-aware logs, completed-month retention, and manual verification.
- `README.md` — describe the Sep–Dec selector and current-plus-future-month updater behavior.

### Intentionally unchanged

- `calendar.js` — it already derives ICS dates from each event's full `YYYY-MM-DD` value and works across months.
- `.github/workflows/update-events.yml` — it already installs Chromium, runs pytest, runs the updater, validates both county JSON files, commits `last-updated.json`, and deploys through the existing Pages flow.
- `sources.json` — source coverage is independent from the Sep–Dec orchestration change.
- `miami-events.json` / `broward-events.json` schema — same files and same event fields; future-month records append into these archives.

---

### Task 1: Add Shared Month and Date Arithmetic

**Files:**
- Create: `dashboard-months.js`
- Create: `tests/test_dashboard_months.py`

**Interfaces:**
- Produces: `SFMonths.SUPPORTED_MONTHS: string[]`
- Produces: `SFMonths.defaultMonth(now: Date) -> string`
- Produces: `SFMonths.monthMeta(monthKey: string) -> {key,label,year,monthIndex,days,firstWeekday}`
- Produces: `SFMonths.eventInMonth(dateString: string, monthKey: string) -> boolean`
- Produces: `SFMonths.sameMonth(now: Date, monthKey: string) -> boolean`
- Produces: `SFMonths.currentWeekDateKeys(now: Date) -> string[]`
- Produces: `SFMonths.currentWeekendDateKeys(now: Date) -> string[]`
- Consumed by: `miami.html`, `broward.html`, `tests/test_dashboard_multimonth_browser.py`

- [ ] **Step 1: Write failing Node-backed unit tests**

Create `tests/test_dashboard_months.py`:

```python
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MONTHS_JS = ROOT / "dashboard-months.js"


def run_node(expression: str):
    script = f"""
const months = require({json.dumps(str(MONTHS_JS))});
const result = {expression};
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def test_supported_months_are_sep_through_dec_2026():
    assert run_node("months.SUPPORTED_MONTHS") == [
        "2026-09", "2026-10", "2026-11", "2026-12"
    ]


def test_default_month_uses_current_month_and_clamps_outside_range():
    assert run_node("months.defaultMonth(new Date(2026, 8, 10))") == "2026-09"
    assert run_node("months.defaultMonth(new Date(2026, 9, 10))") == "2026-10"
    assert run_node("months.defaultMonth(new Date(2026, 10, 10))") == "2026-11"
    assert run_node("months.defaultMonth(new Date(2026, 11, 10))") == "2026-12"
    assert run_node("months.defaultMonth(new Date(2026, 5, 10))") == "2026-09"
    assert run_node("months.defaultMonth(new Date(2027, 0, 10))") == "2026-12"


def test_month_geometry_is_dynamic():
    assert run_node("months.monthMeta('2026-09')") == {
        "key": "2026-09", "label": "September 2026", "year": 2026,
        "monthIndex": 8, "days": 30, "firstWeekday": 2,
    }
    assert run_node("months.monthMeta('2026-10')") == {
        "key": "2026-10", "label": "October 2026", "year": 2026,
        "monthIndex": 9, "days": 31, "firstWeekday": 4,
    }
    assert run_node("months.monthMeta('2026-11')") == {
        "key": "2026-11", "label": "November 2026", "year": 2026,
        "monthIndex": 10, "days": 30, "firstWeekday": 0,
    }
    assert run_node("months.monthMeta('2026-12')") == {
        "key": "2026-12", "label": "December 2026", "year": 2026,
        "monthIndex": 11, "days": 31, "firstWeekday": 2,
    }


def test_event_month_and_current_month_checks_use_full_year_month():
    assert run_node("months.eventInMonth('2026-10-31','2026-10')") is True
    assert run_node("months.eventInMonth('2026-09-30','2026-10')") is False
    assert run_node("months.sameMonth(new Date(2026, 9, 3),'2026-10')") is True
    assert run_node("months.sameMonth(new Date(2026, 8, 30),'2026-10')") is False


def test_current_week_is_sunday_through_saturday_and_weekend_is_fri_to_sun():
    assert run_node("months.currentWeekDateKeys(new Date(2026, 8, 10))") == [
        "2026-09-06", "2026-09-07", "2026-09-08", "2026-09-09",
        "2026-09-10", "2026-09-11", "2026-09-12",
    ]
    assert run_node("months.currentWeekendDateKeys(new Date(2026, 8, 10))") == [
        "2026-09-11", "2026-09-12", "2026-09-13"
    ]
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m pytest tests/test_dashboard_months.py -q
```

Expected: FAIL because `dashboard-months.js` does not exist.

- [ ] **Step 3: Implement the shared helper**

Create `dashboard-months.js`:

```javascript
(function (global) {
  'use strict';

  const SUPPORTED_MONTHS = ['2026-09', '2026-10', '2026-11', '2026-12'];
  const FIRST_MONTH = SUPPORTED_MONTHS[0];
  const LAST_MONTH = SUPPORTED_MONTHS[SUPPORTED_MONTHS.length - 1];

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function localDateKey(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function localMonthKey(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
  }

  function defaultMonth(now) {
    const key = localMonthKey(now);
    if (key <= FIRST_MONTH) return FIRST_MONTH;
    if (key >= LAST_MONTH) return LAST_MONTH;
    return SUPPORTED_MONTHS.includes(key) ? key : FIRST_MONTH;
  }

  function monthMeta(monthKey) {
    if (!SUPPORTED_MONTHS.includes(monthKey)) {
      throw new Error(`Unsupported month: ${monthKey}`);
    }
    const [yearText, monthText] = monthKey.split('-');
    const year = Number(yearText);
    const monthIndex = Number(monthText) - 1;
    const first = new Date(year, monthIndex, 1);
    const days = new Date(year, monthIndex + 1, 0).getDate();
    const label = first.toLocaleString('en-US', { month: 'long', year: 'numeric' });
    return { key: monthKey, label, year, monthIndex, days, firstWeekday: first.getDay() };
  }

  function eventInMonth(dateString, monthKey) {
    return String(dateString || '').slice(0, 7) === monthKey;
  }

  function sameMonth(now, monthKey) {
    return localMonthKey(now) === monthKey;
  }

  function addLocalDays(date, days) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
  }

  function currentWeekDateKeys(now) {
    const start = addLocalDays(now, -now.getDay());
    return Array.from({ length: 7 }, (_, index) => localDateKey(addLocalDays(start, index)));
  }

  function currentWeekendDateKeys(now) {
    const start = addLocalDays(now, -now.getDay());
    return [5, 6, 7].map(offset => localDateKey(addLocalDays(start, offset)));
  }

  const api = {
    SUPPORTED_MONTHS,
    defaultMonth,
    monthMeta,
    eventInMonth,
    sameMonth,
    currentWeekDateKeys,
    currentWeekendDateKeys,
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.SFMonths = api;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run the helper tests and verify GREEN**

Run:

```bash
python -m pytest tests/test_dashboard_months.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit the helper and tests**

```bash
git add dashboard-months.js tests/test_dashboard_months.py
git commit -m "feat: add shared dashboard month helpers"
```

---

### Task 2: Make the Daily Updater Scan Current and Future 2026 Months

**Files:**
- Modify: `scripts/update_events.py:1-101`
- Modify: `tests/test_runner.py`

**Interfaces:**
- Produces: `current_eastern_time() -> datetime`
- Produces: `tracked_months(now: datetime) -> list[tuple[int, int]]`
- Produces: `update_county_months(county: str, sources: list[dict], months: list[tuple[int,int]], root: Path = ROOT) -> tuple[int,int,list[str]]`
- Preserves: `update_county(county, sources, year, month, root) -> tuple[int,int,list[str]]` as a compatibility wrapper around one month.
- Consumes: existing `collect_source`, `merge_events`, `validate_dataset`, county JSON files, `sources.json`.

- [ ] **Step 1: Add failing tracking-window tests**

Append to `tests/test_runner.py`:

```python
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
```

- [ ] **Step 2: Add failing multi-month orchestration tests**

Append:

```python
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
```

- [ ] **Step 3: Run the new runner tests and verify RED**

Run:

```bash
python -m pytest tests/test_runner.py -q
```

Expected: FAIL because `tracked_months` and `update_county_months` do not exist and warnings are not month-aware.

- [ ] **Step 4: Implement the tracking window and multi-month county orchestration**

Refactor `scripts/update_events.py` around these exact helpers:

```python
TRACKING_YEAR = 2026
TRACKING_START_MONTH = 9
TRACKING_END_MONTH = 12
EASTERN = ZoneInfo("America/New_York")


def current_eastern_time() -> datetime:
    return datetime.now(EASTERN)


def tracked_months(now: datetime) -> list[tuple[int, int]]:
    stamp = now if now.tzinfo else now.replace(tzinfo=EASTERN)
    stamp = stamp.astimezone(EASTERN)
    if stamp.year > TRACKING_YEAR:
        return []
    if stamp.year < TRACKING_YEAR:
        start = TRACKING_START_MONTH
    else:
        start = max(TRACKING_START_MONTH, stamp.month)
    if start > TRACKING_END_MONTH:
        return []
    return [(TRACKING_YEAR, month) for month in range(start, TRACKING_END_MONTH + 1)]


def county_label(county: str) -> str:
    return "Broward" if county == "broward" else "Miami"
```

Replace the body of county collection with one load/merge/write cycle:

```python
def update_county_months(
    county: str,
    sources: list[dict],
    months: list[tuple[int, int]],
    root: Path = ROOT,
) -> tuple[int, int, list[str]]:
    filename = "broward-events.json" if county == "broward" else "miami-events.json"
    path = root / filename
    existing = load_json(path, [])
    discovered = []
    warnings = []
    label = county_label(county)

    for year, month in months:
        month_key = f"{year:04d}-{month:02d}"
        for source in sources:
            prefix = f"{label} {month_key} / {source['name']}"
            if source.get("enabled", True) is False:
                print(f"[SKIP] {prefix}: disabled")
                continue

            result = collect_source(source, year, month)
            if result.status == "ok":
                if source.get("warn_on_empty") and not result.events:
                    line = f"{prefix}: ok but returned 0 events"
                    warnings.append(line)
                    print(f"[WARN] {line}")
                else:
                    print(f"[OK] {prefix}: {len(result.events)} events")
                discovered.extend(result.events)
            elif result.status == "disabled":
                print(f"[SKIP] {prefix}: disabled")
            else:
                line = f"{prefix}: {result.status}: {result.message}"
                warnings.append(line)
                print(f"[WARN] {line}")

    merged = merge_events(existing, discovered)
    errors = validate_dataset(merged, previous_count=len(existing))
    if errors:
        raise RuntimeError("; ".join(errors))

    path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(existing), len(merged), warnings


def update_county(
    county: str,
    sources: list[dict],
    year: int,
    month: int,
    root: Path = ROOT,
) -> tuple[int, int, list[str]]:
    return update_county_months(county, sources, [(year, month)], root)
```

Update `main()` so it computes months once, writes each county once, and writes the timestamp once:

```python
def main() -> int:
    registry = load_json(ROOT / "sources.json", {})
    now = current_eastern_time()
    months = tracked_months(now)

    if months:
        month_text = ",".join(f"{year:04d}-{month:02d}" for year, month in months)
        for county in ("broward", "miami"):
            before, after, warnings = update_county_months(
                county,
                registry.get(county, []),
                months,
                ROOT,
            )
            print(
                f"[DONE] {county}: {before} -> {after}; "
                f"months={month_text}; warnings={len(warnings)}"
            )
    else:
        print("[DONE] no supported discovery months remain after 2026-12")

    metadata = write_last_updated(ROOT, now=now)
    print(f"[DONE] last updated: {metadata['updated_at']}")
    return 0
```

- [ ] **Step 5: Update the old empty-warning assertion for the compatibility wrapper**

Change the final assertion in `test_expected_nonempty_source_reports_warning_when_zero_events` from:

```python
assert warnings == ["Shotgun Miami: ok but returned 0 events"]
```

to:

```python
assert warnings == ["Miami 2026-09 / Shotgun Miami: ok but returned 0 events"]
```

- [ ] **Step 6: Add a single timestamp-write test**

Append:

```python
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
```

- [ ] **Step 7: Run runner tests and verify GREEN**

Run:

```bash
python -m pytest tests/test_runner.py -q
```

Expected: all runner tests pass.

- [ ] **Step 8: Commit the updater refactor**

```bash
git add scripts/update_events.py tests/test_runner.py
git commit -m "feat: scan remaining 2026 months in daily updater"
```

---

### Task 3: Support Confident Material Event Changes Across Months

**Files:**
- Modify: `scripts/events/merge.py`
- Modify: `tests/test_merge.py`

**Interfaces:**
- Produces: `canonical_url(value: str) -> str`
- Produces: `name_identity(value: str) -> str`
- Extends: `merge_events(existing, discovered)` so a same-name event with the same event-specific URL can move date/time/venue without leaving the old record behind.
- Safety rule: URL-backed material replacement is allowed only when the canonical URL appears exactly once in the existing dataset and the normalized semantic event name matches after removing cancellation/postponement status words.

- [ ] **Step 1: Add failing material-change tests**

Append to `tests/test_merge.py`:

```python
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
```

- [ ] **Step 2: Run merge tests and verify RED**

Run:

```bash
python -m pytest tests/test_merge.py -q
```

Expected: the date/venue-change and cancellation tests fail because the current merge identity includes date/name/venue/time and cannot replace the old record.

- [ ] **Step 3: Implement canonical URL and semantic-name identity**

At the top of `scripts/events/merge.py`, add:

```python
from collections import Counter
from urllib.parse import urlsplit
```

Add these helpers below `_norm`:

```python
_STATUS_WORDS = re.compile(r"\b(cancelled|canceled|postponed|rescheduled)\b", re.I)


def canonical_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parts = urlsplit(text)
    path = parts.path.rstrip("/") or "/"
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}"


def name_identity(value: str) -> str:
    return _norm(_STATUS_WORDS.sub("", str(value or "")))
```

Refactor `merge_events` so exact event keys still win first, then unique-URL + semantic-name matches may replace material identity fields:

```python
def _merge_fields(current: dict, incoming: dict, material: bool = False) -> dict:
    if material:
        for field in ("date", "name", "venue", "city"):
            value = incoming.get(field)
            if value not in (None, ""):
                current[field] = value
        current["time"] = incoming.get("time") or current.get("time", "")
    else:
        current["time"] = _prefer_time(current.get("time", ""), incoming.get("time", ""))

    for field in ("url", "cost", "source", "city", "venue", "category", "age"):
        value = incoming.get(field)
        if value not in (None, "", "Check source"):
            current[field] = value

    current["featured"] = bool(current.get("featured") or incoming.get("featured"))
    current["new"] = False
    return current


def merge_events(existing: list[dict], discovered: list[dict]) -> list[dict]:
    out = {event_key(e): dict(e) for e in existing}
    url_counts = Counter(canonical_url(e.get("url")) for e in existing if canonical_url(e.get("url")))

    for event in discovered:
        key = event_key(event)
        if key in out:
            out[key] = _merge_fields(out[key], event)
            continue

        incoming_url = canonical_url(event.get("url"))
        material_key = None
        if incoming_url and url_counts[incoming_url] == 1:
            for old_key, current in out.items():
                if (
                    canonical_url(current.get("url")) == incoming_url
                    and name_identity(current.get("name")) == name_identity(event.get("name"))
                ):
                    material_key = old_key
                    break

        if material_key is not None:
            current = out.pop(material_key)
            current = _merge_fields(current, event, material=True)
            out[event_key(current)] = current
            continue

        out[key] = dict(event)

    return sorted(
        out.values(),
        key=lambda e: (
            e.get("date", ""), e.get("time", ""), e.get("name", ""), e.get("venue", "")
        ),
    )
```

- [ ] **Step 4: Run merge tests and verify GREEN**

Run:

```bash
python -m pytest tests/test_merge.py -q
```

Expected: all merge tests pass.

- [ ] **Step 5: Run runner + validation regression tests**

```bash
python -m pytest tests/test_runner.py tests/test_validate.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit material-change merge support**

```bash
git add scripts/events/merge.py tests/test_merge.py
git commit -m "feat: merge confident event schedule changes"
```

---

### Task 4: Add Multi-Month UX to the Miami-Dade Dashboard

**Files:**
- Modify: `miami.html`
- Modify: `tests/test_dashboard_features.py`
- Create: `tests/test_dashboard_multimonth_browser.py`

**Interfaces:**
- Consumes: `window.SFMonths` from `dashboard-months.js`.
- State: `selectedMonth: string`, `selectedDay: number | null`, existing `mode` and existing input/select values.
- DOM: add `#month` selector and `#monthHeading` calendar heading.
- Data pipeline: all events → selected month → city/category/price/search → mode → selected day → sort.

- [ ] **Step 1: Add failing static feature assertions for Miami**

Append to `tests/test_dashboard_features.py`:

```python
def test_miami_has_sep_dec_month_selector_and_shared_month_script():
    html = read_dashboard("miami.html")
    assert '<script src="dashboard-months.js"></script>' in html
    assert 'id="month"' in html
    for value, label in (
        ("2026-09", "September 2026"),
        ("2026-10", "October 2026"),
        ("2026-11", "November 2026"),
        ("2026-12", "December 2026"),
    ):
        assert f'<option value="{value}">{label}</option>' in html
    assert 'id="monthHeading"' in html
    assert 'SFMonths.defaultMonth(new Date())' in html
    assert 'SFMonths.monthMeta(selectedMonth)' in html
    assert 'SFMonths.eventInMonth(e.date,selectedMonth)' in html
```

- [ ] **Step 2: Add Playwright test infrastructure and failing Miami behavior tests**

Create `tests/test_dashboard_multimonth_browser.py`:

```python
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

TEST_EVENTS = [
    {
        "date": "2026-09-10", "time": "7:00 PM", "name": "September Test",
        "venue": "Miami Venue", "city": "Miami", "category": "Concert",
        "cost": "Free", "url": "https://example.com/september", "source": "Test",
        "age": "", "featured": False, "new": True,
    },
    {
        "date": "2026-10-05", "time": "8:00 PM", "name": "October Test",
        "venue": "Miami Venue", "city": "Miami", "category": "Concert",
        "cost": "$20", "url": "https://example.com/october", "source": "Test",
        "age": "18+", "featured": True, "new": True,
    },
]


@contextmanager
def serve_repo():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def open_dashboard(filename, data_url_pattern):
    manager = sync_playwright()
    playwright = manager.start()
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.route(
        data_url_pattern,
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(TEST_EVENTS),
        ),
    )
    return manager, browser, page


def test_miami_switching_month_resets_day_but_keeps_search_and_filters():
    with serve_repo() as base:
        manager, browser, page = open_dashboard("miami.html", "**/miami-events.json")
        try:
            page.goto(f"{base}/miami.html")
            page.select_option("#month", "2026-09")
            page.fill("#search", "Test")
            page.select_option("#city", "Miami")
            page.locator('[data-d="10"]').click()
            assert page.locator("#sel").inner_text() == "10"

            page.select_option("#month", "2026-10")
            assert page.locator("#sel").inner_text() == "All"
            assert page.locator("#search").input_value() == "Test"
            assert page.locator("#city").input_value() == "Miami"
            assert page.locator("#monthHeading").inner_text() == "October 2026"
            assert page.locator("#cal [data-d]").count() == 31
            assert page.locator("#list").inner_text().count("October Test") == 1
            assert "September Test" not in page.locator("#list").inner_text()
        finally:
            browser.close()
            manager.stop()


def test_miami_favorite_persists_across_month_switches():
    with serve_repo() as base:
        manager, browser, page = open_dashboard("miami.html", "**/miami-events.json")
        try:
            page.goto(f"{base}/miami.html")
            page.select_option("#month", "2026-10")
            page.locator(".fav-btn").click()
            assert page.locator(".fav-btn").inner_text() == "★"

            page.select_option("#month", "2026-09")
            page.select_option("#month", "2026-10")
            assert page.locator(".fav-btn").inner_text() == "★"

            page.locator('[data-mode="favorites"].chip').click()
            assert "October Test" in page.locator("#list").inner_text()
        finally:
            browser.close()
            manager.stop()


def test_miami_empty_supported_month_uses_friendly_message_and_renders_dates():
    with serve_repo() as base:
        manager, browser, page = open_dashboard("miami.html", "**/miami-events.json")
        try:
            page.goto(f"{base}/miami.html")
            page.select_option("#month", "2026-12")
            assert page.locator("#cal [data-d]").count() == 31
            assert page.locator("#list").inner_text() == (
                "No events found yet — check back as new events are announced."
            )
        finally:
            browser.close()
            manager.stop()
```

- [ ] **Step 3: Run the Miami dashboard tests and verify RED**

Run:

```bash
python -m pytest tests/test_dashboard_features.py tests/test_dashboard_multimonth_browser.py -q
```

Expected: FAIL because Miami has no month selector, no shared month helper script, and a fixed September calendar.

- [ ] **Step 4: Add the Miami month selector markup and responsive toolbar sizing**

In `miami.html`, load the month helper immediately after `calendar.js`:

```html
<script src="calendar.js"></script>
<script src="dashboard-months.js"></script>
```

Add the month selector as the first select after search:

```html
<select id="month" aria-label="Month">
  <option value="2026-09">September 2026</option>
  <option value="2026-10">October 2026</option>
  <option value="2026-11">November 2026</option>
  <option value="2026-12">December 2026</option>
</select>
```

Change only the desktop toolbar grid column declaration from:

```css
grid-template-columns:2fr repeat(3,minmax(150px,1fr)) auto
```

to:

```css
grid-template-columns:2fr repeat(4,minmax(140px,1fr)) auto
```

The existing `@media(max-width:1050px)` and `@media(max-width:650px)` rules continue collapsing the toolbar; do not remove them.

Give the calendar heading a stable id:

```html
<h2 id="monthHeading">September 2026</h2>
```

Change the page title so it is not September-specific:

```html
<title>Miami-Dade Events Radar — Sep–Dec 2026</title>
```

- [ ] **Step 5: Replace fixed September state with selected-month state**

Replace the element/state setup with:

```javascript
const search=document.getElementById('search'),month=document.getElementById('month'),city=document.getElementById('city'),cat=document.getElementById('cat'),price=document.getElementById('price'),cal=document.getElementById('cal'),list=document.getElementById('list');
let selectedDay=null,mode='all',selectedMonth=SFMonths.defaultMonth(new Date());
month.value=selectedMonth;
```

Inside `boot()`, replace `base()` and `modeFilter()` with month-aware versions:

```javascript
function isFree(e){return /free/i.test(e.cost||'')}
function monthEvents(){return events.filter(e=>SFMonths.eventInMonth(e.date,selectedMonth))}
function base(){
 const q=search.value.trim().toLowerCase();
 return monthEvents().filter(e=>(!city.value||e.city===city.value)&&(!cat.value||e.category===cat.value)&&(!price.value||(price.value==='free'?isFree(e):!isFree(e)))&&(!q||[e.name,e.venue,e.city,e.category,e.source,e.cost].join(' ').toLowerCase().includes(q)));
}
function modeFilter(arr){
 const now=new Date();
 if(mode==='week'){
  const keys=new Set(SFMonths.currentWeekDateKeys(now));
  return arr.filter(e=>keys.has(e.date));
 }
 if(mode==='weekend'){
  const keys=new Set(SFMonths.currentWeekendDateKeys(now));
  return arr.filter(e=>keys.has(e.date));
 }
 if(mode==='new') return arr.filter(e=>e.new);
 if(mode==='featured') return arr.filter(e=>e.featured);
 if(mode==='favorites') return arr.filter(e=>isFavorite(e));
 return arr;
}
```

Keep `filtered()` in the same order: mode after month/normal filters, then selected day, then sort.

- [ ] **Step 6: Replace fixed calendar geometry and today highlighting**

Replace `renderCal()` with:

```javascript
function renderCal(){
 const arr=modeFilter(base()),meta=SFMonths.monthMeta(selectedMonth),now=new Date();
 let h='';
 for(let i=0;i<meta.firstWeekday;i++)h+='<div class="day blank"></div>';
 for(let d=1;d<=meta.days;d++){
  const es=arr.filter(e=>+e.date.slice(-2)===d),cls=['day'];
  if(d===selectedDay)cls.push('active');
  if(SFMonths.sameMonth(now,selectedMonth)&&d===now.getDate())cls.push('today');
  h+=`<button class="${cls.join(' ')}" data-d="${d}"><span class="num">${d}</span>${es.slice(0,4).map(e=>`<span class="evt ${e.featured?'hot':''} ${e.new?'new':''}" title="${esc(e.name)}">${esc(e.name)}</span>`).join('')}${es.length>4?`<span class="evt">+${es.length-4} more</span>`:''}</button>`;
 }
 cal.innerHTML=h;
 cal.querySelectorAll('[data-d]').forEach(b=>b.onclick=()=>{const d=+b.dataset.d;selectedDay=selectedDay===d?null:d;render()});
}
```

- [ ] **Step 7: Make stats, headings, and empty states month-aware**

Replace the fixed title/stats section inside `render()` with:

```javascript
const f=filtered(),scoped=base(),meta=SFMonths.monthMeta(selectedMonth),weekKeys=new Set(SFMonths.currentWeekDateKeys(new Date()));
document.getElementById('monthHeading').textContent=meta.label;
document.getElementById('count').textContent=f.length;
document.getElementById('weekCount').textContent=scoped.filter(e=>weekKeys.has(e.date)).length;
document.getElementById('freeCount').textContent=f.filter(isFree).length;
document.getElementById('sourceCount').textContent=uniq(f.map(e=>e.source)).length;
document.getElementById('sel').textContent=selectedDay||'All';
document.getElementById('title').textContent=selectedDay?`${meta.label.replace(' 2026','')} ${selectedDay}`:(mode==='week'?'This week':mode==='weekend'?'This weekend':mode==='new'?'Newly added':mode==='featured'?'Featured events':mode==='favorites'?'Favorite events':'All events');
document.getElementById('results').textContent=`${f.length} matching events`;
document.getElementById('status').textContent=`${modeFilter(base()).length} events on calendar`;
```

Keep the existing event-card HTML, but set the empty string by distinguishing an empty month from filtered-out results:

```javascript
const emptyText=monthEvents().length===0?'No events found yet — check back as new events are announced.':'No matching events.';
list.innerHTML=f.length?f.map(e=>`<article class="card">${e.new?'<div class="newb">NEWLY ADDED</div>':''}<div class="top"><h3>${esc(e.name)}</h3><div class="card-tools"><button class="fav-btn ${isFavorite(e)?'active':''}" data-fav-key="${esc(eventKey(e))}" aria-label="${isFavorite(e)?'Remove from favorites':'Add to favorites'}" title="${isFavorite(e)?'Remove from favorites':'Add to favorites'}">${isFavorite(e)?'★':'☆'}</button><span class="badge">${esc(e.category)}</span></div></div><div class="meta"><b>${esc(e.date.slice(5).replace('-','/'))} • ${esc(e.time)}</b><br><span class="muted">${esc(e.venue)} • ${esc(e.city)}</span>${e.age?`<br>${esc(e.age)}`:''}<br><span class="price">${esc(e.cost)}</span><br><span class="source">Source: ${esc(e.source)}</span></div><div class="card-actions"><a class="btn" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">Event / Tickets ↗</a><button class="calendar-btn" data-cal-key="${esc(eventKey(e))}" type="button">📅 Add to Calendar</button></div></article>`).join(''):`<div class="empty">${emptyText}</div>`;
```

Preserve Miami's county-specific storage/data constants exactly:

```javascript
const DATA_URL="miami-events.json";
const LAST_UPDATED_URL="last-updated.json";
const FAVORITES_KEY="sf-events-favorites-miami-v1";
```

Do not change `eventKey` or `SFCalendar.downloadEvent(event)`.

- [ ] **Step 8: Wire month changes without clearing other filters or favorites**

Add:

```javascript
month.addEventListener('change',()=>{
 selectedMonth=month.value;
 selectedDay=null;
 render();
});
```

Keep the current city/category/price/search listeners. Update Clear so it clears search/city/category/price/day/mode but leaves `selectedMonth` unchanged:

```javascript
document.getElementById('clear').onclick=()=>{search.value='';city.value='';cat.value='';price.value='';selectedDay=null;mode='all';syncModeControls();render()};
```

- [ ] **Step 9: Run Miami static + browser tests and verify GREEN**

Run:

```bash
python -m pytest tests/test_dashboard_features.py tests/test_dashboard_multimonth_browser.py -q
```

Expected: all current Miami multi-month tests pass; Broward multi-month assertions are not added until Task 5.

- [ ] **Step 10: Commit the Miami dashboard**

```bash
git add miami.html tests/test_dashboard_features.py tests/test_dashboard_multimonth_browser.py
git commit -m "feat: add Sep-Dec selector to Miami dashboard"
```

---

### Task 5: Mirror Multi-Month UX in the Broward Dashboard

**Files:**
- Modify: `broward.html`
- Modify: `tests/test_dashboard_features.py`
- Modify: `tests/test_dashboard_multimonth_browser.py`

**Interfaces:**
- Same `SFMonths` interface and state behavior as Miami.
- Preserve Broward-only values: `DATA_URL="broward-events.json"`, `FAVORITES_KEY="sf-events-favorites-broward-v1"`, Broward labels and hero copy.

- [ ] **Step 1: Generalize the static selector test to both dashboards**

Replace the Miami-only selector test in `tests/test_dashboard_features.py` with:

```python
def test_both_dashboards_have_sep_dec_month_selector_and_shared_month_script():
    for filename in ("miami.html", "broward.html"):
        html = read_dashboard(filename)
        assert '<script src="dashboard-months.js"></script>' in html
        assert 'id="month"' in html
        for value, label in (
            ("2026-09", "September 2026"),
            ("2026-10", "October 2026"),
            ("2026-11", "November 2026"),
            ("2026-12", "December 2026"),
        ):
            assert f'<option value="{value}">{label}</option>' in html
        assert 'id="monthHeading"' in html
        assert 'SFMonths.defaultMonth(new Date())' in html
        assert 'SFMonths.monthMeta(selectedMonth)' in html
        assert 'SFMonths.eventInMonth(e.date,selectedMonth)' in html
```

- [ ] **Step 2: Add a failing Broward browser smoke test**

Append to `tests/test_dashboard_multimonth_browser.py`:

```python
def test_broward_switches_to_november_with_dynamic_30_day_calendar():
    broward_events = [
        dict(TEST_EVENTS[0], date="2026-09-12", name="Broward September", city="Fort Lauderdale"),
        dict(TEST_EVENTS[1], date="2026-11-21", name="Broward November", city="Hollywood"),
    ]
    with serve_repo() as base:
        manager = sync_playwright()
        playwright = manager.start()
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.route(
            "**/broward-events.json",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(broward_events),
            ),
        )
        try:
            page.goto(f"{base}/broward.html")
            page.select_option("#month", "2026-11")
            assert page.locator("#monthHeading").inner_text() == "November 2026"
            assert page.locator("#cal [data-d]").count() == 30
            assert "Broward November" in page.locator("#list").inner_text()
            assert "Broward September" not in page.locator("#list").inner_text()
        finally:
            browser.close()
            manager.stop()
```

- [ ] **Step 3: Run Broward-related tests and verify RED**

Run:

```bash
python -m pytest tests/test_dashboard_features.py tests/test_dashboard_multimonth_browser.py -q
```

Expected: FAIL on Broward because `broward.html` is still September-only.

- [ ] **Step 4: Apply the approved Miami month behavior to Broward without changing county-specific configuration**

Apply these exact structural changes in `broward.html`:

Change the title to:

```html
<title>Broward Events Radar — Sep–Dec 2026</title>
```

Insert this selector after the search input and before the city selector:

```html
<select id="month" aria-label="Month">
  <option value="2026-09">September 2026</option>
  <option value="2026-10">October 2026</option>
  <option value="2026-11">November 2026</option>
  <option value="2026-12">December 2026</option>
</select>
```

Change the calendar heading to:

```html
<h2 id="monthHeading">September 2026</h2>
```

Load the shared helper immediately after `calendar.js`:

```html
<script src="calendar.js"></script>
<script src="dashboard-months.js"></script>
```

Change only the desktop toolbar grid column declaration from:

```css
grid-template-columns:2fr repeat(3,minmax(150px,1fr)) auto
```

to:

```css
grid-template-columns:2fr repeat(4,minmax(140px,1fr)) auto
```

Retain these Broward constants exactly:

```javascript
const DATA_URL="broward-events.json";
const LAST_UPDATED_URL="last-updated.json";
const FAVORITES_KEY="sf-events-favorites-broward-v1";
```

Replace Broward's fixed element/state setup with:

```javascript
const search=document.getElementById('search'),month=document.getElementById('month'),city=document.getElementById('city'),cat=document.getElementById('cat'),price=document.getElementById('price'),cal=document.getElementById('cal'),list=document.getElementById('list');
let selectedDay=null,mode='all',selectedMonth=SFMonths.defaultMonth(new Date());
month.value=selectedMonth;
```

Replace Broward's `base()` and `modeFilter()` with:

```javascript
function isFree(e){return /free/i.test(e.cost||'')}
function monthEvents(){return events.filter(e=>SFMonths.eventInMonth(e.date,selectedMonth))}
function base(){
 const q=search.value.trim().toLowerCase();
 return monthEvents().filter(e=>(!city.value||e.city===city.value)&&(!cat.value||e.category===cat.value)&&(!price.value||(price.value==='free'?isFree(e):!isFree(e)))&&(!q||[e.name,e.venue,e.city,e.category,e.source,e.cost].join(' ').toLowerCase().includes(q)));
}
function modeFilter(arr){
 const now=new Date();
 if(mode==='week'){
  const keys=new Set(SFMonths.currentWeekDateKeys(now));
  return arr.filter(e=>keys.has(e.date));
 }
 if(mode==='weekend'){
  const keys=new Set(SFMonths.currentWeekendDateKeys(now));
  return arr.filter(e=>keys.has(e.date));
 }
 if(mode==='new') return arr.filter(e=>e.new);
 if(mode==='featured') return arr.filter(e=>e.featured);
 if(mode==='favorites') return arr.filter(e=>isFavorite(e));
 return arr;
}
```

Replace Broward's `renderCal()` with:

```javascript
function renderCal(){
 const arr=modeFilter(base()),meta=SFMonths.monthMeta(selectedMonth),now=new Date();
 let h='';
 for(let i=0;i<meta.firstWeekday;i++)h+='<div class="day blank"></div>';
 for(let d=1;d<=meta.days;d++){
  const es=arr.filter(e=>+e.date.slice(-2)===d),cls=['day'];
  if(d===selectedDay)cls.push('active');
  if(SFMonths.sameMonth(now,selectedMonth)&&d===now.getDate())cls.push('today');
  h+=`<button class="${cls.join(' ')}" data-d="${d}"><span class="num">${d}</span>${es.slice(0,4).map(e=>`<span class="evt ${e.featured?'hot':''} ${e.new?'new':''}" title="${esc(e.name)}">${esc(e.name)}</span>`).join('')}${es.length>4?`<span class="evt">+${es.length-4} more</span>`:''}</button>`;
 }
 cal.innerHTML=h;
 cal.querySelectorAll('[data-d]').forEach(b=>b.onclick=()=>{const d=+b.dataset.d;selectedDay=selectedDay===d?null:d;render()});
}
```

Replace the fixed Broward stats/title block inside `render()` with:

```javascript
const f=filtered(),scoped=base(),meta=SFMonths.monthMeta(selectedMonth),weekKeys=new Set(SFMonths.currentWeekDateKeys(new Date()));
document.getElementById('monthHeading').textContent=meta.label;
document.getElementById('count').textContent=f.length;
document.getElementById('weekCount').textContent=scoped.filter(e=>weekKeys.has(e.date)).length;
document.getElementById('freeCount').textContent=f.filter(isFree).length;
document.getElementById('sourceCount').textContent=uniq(f.map(e=>e.source)).length;
document.getElementById('sel').textContent=selectedDay||'All';
document.getElementById('title').textContent=selectedDay?`${meta.label.replace(' 2026','')} ${selectedDay}`:(mode==='week'?'This week':mode==='weekend'?'This weekend':mode==='new'?'Newly added':mode==='featured'?'Featured events':mode==='favorites'?'Favorite events':'All events');
document.getElementById('results').textContent=`${f.length} matching events`;
document.getElementById('status').textContent=`${modeFilter(base()).length} events on calendar`;
const emptyText=monthEvents().length===0?'No events found yet — check back as new events are announced.':'No matching events.';
list.innerHTML=f.length?f.map(e=>`<article class="card">${e.new?'<div class="newb">NEWLY ADDED</div>':''}<div class="top"><h3>${esc(e.name)}</h3><div class="card-tools"><button class="fav-btn ${isFavorite(e)?'active':''}" data-fav-key="${esc(eventKey(e))}" aria-label="${isFavorite(e)?'Remove from favorites':'Add to favorites'}" title="${isFavorite(e)?'Remove from favorites':'Add to favorites'}">${isFavorite(e)?'★':'☆'}</button><span class="badge">${esc(e.category)}</span></div></div><div class="meta"><b>${esc(e.date.slice(5).replace('-','/'))} • ${esc(e.time)}</b><br><span class="muted">${esc(e.venue)} • ${esc(e.city)}</span>${e.age?`<br>${esc(e.age)}`:''}<br><span class="price">${esc(e.cost)}</span><br><span class="source">Source: ${esc(e.source)}</span></div><div class="card-actions"><a class="btn" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">Event / Tickets ↗</a><button class="calendar-btn" data-cal-key="${esc(eventKey(e))}" type="button">📅 Add to Calendar</button></div></article>`).join(''):`<div class="empty">${emptyText}</div>`;
```

Add Broward's month-change handler before the existing quick-mode handlers:

```javascript
month.addEventListener('change',()=>{
 selectedMonth=month.value;
 selectedDay=null;
 render();
});
```

Keep Broward's existing search/city/category/price listeners, favorite button handlers, calendar export handlers, mobile mode syncing, and Clear behavior. Do not copy Miami's data URL, favorites key, hero copy, or county labels.

- [ ] **Step 5: Run all dashboard tests and verify GREEN**

```bash
python -m pytest tests/test_dashboard_months.py tests/test_dashboard_features.py tests/test_dashboard_multimonth_browser.py tests/test_calendar_export.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit Broward multi-month behavior**

```bash
git add broward.html tests/test_dashboard_features.py tests/test_dashboard_multimonth_browser.py
git commit -m "feat: add Sep-Dec selector to Broward dashboard"
```

---

### Task 6: Document Multi-Month Operations and Complete Regression Verification

**Files:**
- Modify: `README-AUTO-UPDATE.md`
- Modify: `README.md`
- Verify: `.github/workflows/update-events.yml`
- Verify: `miami-events.json`
- Verify: `broward-events.json`
- Verify: `last-updated.json`

**Interfaces:**
- Documentation must match the actual `tracked_months()` behavior and month-aware log format.
- Existing GitHub Actions command surface remains unchanged.

- [ ] **Step 1: Update `README.md` with the user-facing month behavior**

Add a concise section containing these exact facts:

```markdown
## Sep–Dec 2026 month selector

Both county dashboards use one page and one county event archive for September through December 2026.

- Choose September, October, November, or December from the Month selector.
- The page defaults to the browser's current month inside the supported range, September before the range, and December after the range.
- Search, city, category, and price filters stay selected when the month changes.
- Favorites are shared across all four months for that county.
- Completed months remain browseable.
- An empty future month displays its calendar and a friendly "check back" message instead of a data error.
```

- [ ] **Step 2: Update `README-AUTO-UPDATE.md` with the scheduler behavior**

Add:

```markdown
## Multi-month discovery window

The scheduled updater keeps the current month and every remaining month through December 2026 fresh:

- September run: September, October, November, December
- October run: October, November, December
- November run: November, December
- December run: December
- After December 2026: no event discovery months are scanned

Completed months remain in `miami-events.json` and `broward-events.json`; a normal daily run does not rescrape them.

Each county file is loaded once, all tracked months are collected with source-level failure isolation, discoveries are merged into the full archive, the full dataset is validated, and the file is written once.

Month-aware logs look like:

```text
[OK] Miami 2026-10 / ZeyZey: 18 events
[WARN] Miami 2026-11 / Resident Advisor: blocked: challenge page
[OK] Broward 2026-12 / Amerant Bank Arena: 7 events
[DONE] miami: 250 -> 338; months=2026-09,2026-10,2026-11,2026-12; warnings=2
```
```

- [ ] **Step 3: Verify the workflow still exercises the full pipeline**

Run:

```bash
python -m pytest tests/test_workflow_config.py -q
```

Expected: all workflow tests pass and the workflow still contains:

```text
python -m playwright install --with-deps chromium
python -m pytest -q
python -m scripts.update_events
python -m scripts.validate_events broward-events.json miami-events.json
last-updated.json
```

- [ ] **Step 4: Run the complete automated test suite**

```bash
python -m pytest -q
```

Expected: zero failures.

- [ ] **Step 5: Validate both county archives explicitly**

```bash
python -m scripts.validate_events broward-events.json miami-events.json
```

Expected: both datasets report `[OK]` with no schema/date errors.

- [ ] **Step 6: Record pre-run counts by month before live collection**

Run:

```bash
python - <<'PY'
import json
from collections import Counter
for filename in ("broward-events.json", "miami-events.json"):
    events=json.load(open(filename, encoding="utf-8"))
    counts=Counter(e["date"][:7] for e in events)
    print(filename, dict(sorted(counts.items())))
PY
```

Save the console output in the implementation notes or PR description so September retention can be compared after the updater run.

- [ ] **Step 7: Run the updater once locally with the real source registry**

```bash
python -m scripts.update_events
```

Expected on a Sep 2026 run: logs contain county + month context for `2026-09`, `2026-10`, `2026-11`, and `2026-12`; individual blocked/empty sources may warn without terminating the run.

- [ ] **Step 8: Revalidate and prove September data was retained**

Run:

```bash
python -m scripts.validate_events broward-events.json miami-events.json
python - <<'PY'
import json
from collections import Counter
for filename in ("broward-events.json", "miami-events.json"):
    events=json.load(open(filename, encoding="utf-8"))
    counts=Counter(e["date"][:7] for e in events)
    assert counts["2026-09"] > 0, (filename, counts)
    print(filename, dict(sorted(counts.items())))
PY
```

Expected: validation passes and both county files still contain September events. October–December counts may be zero for sources that have not yet published events, but no existing future events may disappear.

- [ ] **Step 9: Run the full suite again after the live updater modified JSON**

```bash
python -m pytest -q
```

Expected: zero failures against the final tree.

- [ ] **Step 10: Commit documentation and any verified data refresh**

```bash
git add README.md README-AUTO-UPDATE.md broward-events.json miami-events.json last-updated.json
git commit -m "docs: document multi-month event dashboard operations"
```

If the live updater produced no event JSON changes, commit only the two README files and `last-updated.json` if its timestamp is intentionally part of the rollout snapshot.

---

## Final Verification Checklist

Run these commands immediately before packaging or pushing:

```bash
python -m pytest -q
python -m scripts.validate_events broward-events.json miami-events.json
```

Then verify these concrete UI behaviors in both `miami.html` and `broward.html` using a local server:

```bash
python -m http.server 8000
```

Open each dashboard and confirm:

```text
[ ] Month selector contains Sep / Oct / Nov / Dec 2026.
[ ] Current supported month is selected by default.
[ ] September has 30 date buttons and October/December have 31; November has 30.
[ ] Leading blank cells match each month's actual first weekday.
[ ] Changing month clears Selected day but preserves search/city/category/price.
[ ] Favorite an event, switch months, switch back: the favorite remains.
[ ] Favorites mode shows only favorites in the selected month.
[ ] This week and This weekend show actual browser-current dates only.
[ ] Current-day highlight appears only when viewing the actual current month.
[ ] Empty supported month shows: No events found yet — check back as new events are announced.
[ ] Add to Calendar exports the selected event's actual YYYY-MM-DD date.
[ ] Mobile toolbar remains usable and the month selector has a touch-friendly 48px control height.
[ ] Last-updated timestamp still loads.
```

Inspect one real updater run and confirm the log contains month context:

```text
[OK] Miami 2026-10 / ZeyZey: 18 events
[WARN] Miami 2026-11 / Resident Advisor: blocked: challenge page
[DONE] miami: 250 -> 338; months=2026-09,2026-10,2026-11,2026-12; warnings=2
```

Only after the fresh full test suite, JSON validation, browser smoke check, and updater-log check pass should the repository be packaged for GitHub or pushed.

## Rollout to GitHub

1. Upload/merge the implementation into the existing `south-florida-events-dashboard` repository; do not create a new Pages site.
2. Push to the branch that currently deploys the dashboard.
3. Open **Actions → Update South Florida events → Run workflow**.
4. Confirm the updater Action is green and its log shows county + month collection.
5. Confirm **pages build and deployment** is green.
6. Hard-refresh the existing Miami and Broward dashboard URLs.
7. Switch through Sep, Oct, Nov, and Dec on both dashboards and verify event counts/calendar geometry.
8. Leave the existing daily schedule enabled.
