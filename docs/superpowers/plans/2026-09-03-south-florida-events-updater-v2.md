[south-florida-events-updater-v2-plan.md](https://github.com/user-attachments/files/31805887/south-florida-events-updater-v2-plan.md)
# South Florida Events Updater V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current JSON-LD-only updater with a free hybrid collector engine using HTTP parsing, dedicated adapters, and Playwright fallback so Broward and Miami-Dade discover materially more public events without changing the dashboard event schema.

**Architecture:** Keep GitHub Pages plus `broward-events.json` and `miami-events.json` as the stable interface. Split the updater into collectors, normalization, merge/deduplication, validation, and orchestration modules; route each configured source to HTTP, a dedicated adapter, or Playwright; merge only validated additions/updates into the existing curated files.

**Tech Stack:** Python 3.12, requests, BeautifulSoup4, python-dateutil, Playwright Chromium, pytest, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-03-south-florida-events-updater-v2-design.md`

## Global Constraints

- 100% free: no paid APIs, paid scraping services, subscriptions, or required API keys.
- Keep the exact event keys: `date`, `time`, `name`, `venue`, `city`, `category`, `cost`, `url`, `source`, `age`, `featured`, `new`.
- Do not add `first_seen`, `last_seen`, `verified_source`, `status`, confidence scores, or replacement price/ticket fields.
- A source failure must not fail the whole daily run.
- A failed/empty source must never delete existing curated events.
- Playwright is used only for JavaScript-heavy sites or explicit browser fallback.
- Never bypass CAPTCHAs, authentication, access controls, or rate limits.
- Tests must pass before event JSON is committed.
- The existing dashboards must continue reading the same two JSON files.

---

## Target File Structure

```text
.github/workflows/update-events.yml
requirements.txt
sources.json

scripts/
  update_events.py
  validate_events.py
  collectors/
    __init__.py
    base.py
    router.py
    jsonld.py
    html_cards.py
    browser.py
    arenas.py
    nightlife.py
    comedy_music.py
    municipal.py
    platforms.py
  events/
    __init__.py
    normalize.py
    merge.py
    validate.py
  dev/
    capture_fixture.py

tests/
  conftest.py
  test_normalize.py
  test_merge.py
  test_validate.py
  test_router.py
  test_jsonld_collector.py
  test_html_cards.py
  test_browser_collector.py
  test_arenas.py
  test_nightlife.py
  test_comedy_music.py
  test_municipal.py
  test_platforms.py
  test_runner.py
  fixtures/
```

---

### Task 1: Establish the V2 Test Harness

**Files:**
- Modify: `requirements.txt`
- Create: `tests/conftest.py`
- Create: `tests/test_runner.py`
- Create: `tests/fixtures/jsonld/basic_events.html`

**Interfaces:**
- Produces a pytest foundation and reusable fixture helpers.

- [ ] **Step 1: Add dependencies**

Replace `requirements.txt` with:

```text
requests==2.32.3
beautifulsoup4==4.12.3
python-dateutil==2.9.0.post0
playwright==1.55.0
pytest==8.4.2
```

- [ ] **Step 2: Create test fixtures**

Create `tests/conftest.py`:

```python
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
```

Create `tests/fixtures/jsonld/basic_events.html`:

```html
<!doctype html>
<html>
<head>
<script type="application/ld+json">
[
  {
    "@context": "https://schema.org",
    "@type": "MusicEvent",
    "name": "September Test Concert",
    "startDate": "2026-09-12T20:00:00-04:00",
    "location": {
      "@type": "Place",
      "name": "Test Arena",
      "address": {"addressLocality": "Sunrise"}
    },
    "offers": {
      "@type": "Offer",
      "price": "35.00",
      "priceCurrency": "USD",
      "url": "/tickets/september-test-concert"
    }
  }
]
</script>
</head>
<body></body>
</html>
```

- [ ] **Step 3: Add a schema smoke test**

Create `tests/test_runner.py`:

```python
def test_existing_event_schema(existing_event):
    assert set(existing_event) == {
        "date", "time", "name", "venue", "city", "category",
        "cost", "url", "source", "age", "featured", "new"
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/
git commit -m "test: establish updater v2 harness"
```

---

### Task 2: Extract Event Normalization

**Files:**
- Create: `scripts/events/__init__.py`
- Create: `scripts/events/normalize.py`
- Create: `tests/test_normalize.py`

**Interfaces:**
- `normalize_event(raw: dict, source: dict, page_url: str) -> dict | None`
- `parse_datetime(value) -> datetime | None`

- [ ] **Step 1: Write failing normalization tests**

```python
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
```

- [ ] **Step 2: Verify failure**

```bash
pytest tests/test_normalize.py -q
```

Expected: import failure.

- [ ] **Step 3: Implement `scripts/events/normalize.py`**

```python
from datetime import datetime
from urllib.parse import urljoin
from dateutil import parser as dtparse


def parse_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return dtparse.parse(str(value))
    except (ValueError, TypeError, OverflowError):
        return None


def format_time(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{value.strftime('%M')} {value.strftime('%p')}"


def normalize_event(raw: dict, source: dict, page_url: str) -> dict | None:
    name = str(raw.get("name") or "").strip()
    start = parse_datetime(raw.get("start") or raw.get("startDate"))
    if not name or start is None:
        return None

    url = str(raw.get("url") or page_url)
    if not url.startswith(("http://", "https://")):
        url = urljoin(page_url, url)

    return {
        "date": start.strftime("%Y-%m-%d"),
        "time": str(raw.get("time") or format_time(start)),
        "name": name,
        "venue": str(raw.get("venue") or source["name"]).strip(),
        "city": str(raw.get("city") or source.get("default_city", "")).strip(),
        "category": str(raw.get("category") or "Event").strip(),
        "cost": str(raw.get("cost") or "Check source").strip(),
        "url": url,
        "source": str(raw.get("source") or source["name"]).strip(),
        "age": str(raw.get("age") or "").strip(),
        "featured": bool(raw.get("featured", False)),
        "new": bool(raw.get("new", True)),
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_normalize.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/events tests/test_normalize.py
git commit -m "refactor: extract event normalization"
```

---

### Task 3: Extract Safe Deduplication and Merge

**Files:**
- Create: `scripts/events/merge.py`
- Create: `tests/test_merge.py`

**Interfaces:**
- `event_key(event: dict) -> tuple[str, str, str, str]`
- `merge_events(existing: list[dict], discovered: list[dict]) -> list[dict]`

- [ ] **Step 1: Write failing tests**

```python
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


def test_multiple_same_day_showtimes_survive():
    merged = merge_events(
        [event(name="Disney On Ice", time="3:00 PM")],
        [event(name="Disney On Ice", time="7:00 PM")],
    )
    assert len(merged) == 2


def test_empty_discovery_never_deletes_existing():
    existing = [event()]
    assert merge_events(existing, []) == existing
```

- [ ] **Step 2: Verify failure**

```bash
pytest tests/test_merge.py -q
```

- [ ] **Step 3: Implement merge**

```python
import re


def _norm(value: str) -> str:
    return re.sub(r"\W+", "", str(value or "").lower())


def event_key(event: dict) -> tuple[str, str, str, str]:
    return (
        str(event.get("date", "")),
        _norm(event.get("name", "")),
        _norm(event.get("venue", "")),
        str(event.get("time", "")),
    )


def merge_events(existing: list[dict], discovered: list[dict]) -> list[dict]:
    out = {event_key(e): dict(e) for e in existing}

    for event in discovered:
        key = event_key(event)
        if key not in out:
            out[key] = dict(event)
            continue

        current = out[key]
        for field in ("url", "cost", "source", "city", "venue", "category", "age"):
            incoming = event.get(field)
            if incoming not in (None, "", "Check source"):
                current[field] = incoming

        current["featured"] = bool(current.get("featured") or event.get("featured"))
        current["new"] = False

    return sorted(
        out.values(),
        key=lambda e: (
            e.get("date", ""),
            e.get("time", ""),
            e.get("name", ""),
            e.get("venue", ""),
        ),
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_merge.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/events/merge.py tests/test_merge.py
git commit -m "refactor: add safe event merge and dedupe"
```

---

### Task 4: Add Validation and Destructive-Write Protection

**Files:**
- Create: `scripts/events/validate.py`
- Create: `scripts/validate_events.py`
- Create: `tests/test_validate.py`

**Interfaces:**
- `validate_event(event: dict) -> list[str]`
- `validate_dataset(events: list[dict], previous_count: int | None = None) -> list[str]`

- [ ] **Step 1: Write failing tests**

```python
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


def test_suspicious_count_drop():
    current = [dict(VALID, name=f"Event {i}") for i in range(30)]
    errors = validate_dataset(current, previous_count=130)
    assert any("suspicious count drop" in e for e in errors)
```

- [ ] **Step 2: Implement validator**

```python
from datetime import datetime

REQUIRED_KEYS = {
    "date", "time", "name", "venue", "city", "category",
    "cost", "url", "source", "age", "featured", "new",
}


def validate_event(event: dict) -> list[str]:
    errors = []
    missing = REQUIRED_KEYS - set(event)
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")
    try:
        datetime.strptime(str(event.get("date")), "%Y-%m-%d")
    except ValueError:
        errors.append(f"date must use YYYY-MM-DD: {event.get('date')!r}")
    if not str(event.get("name", "")).strip():
        errors.append("name must not be empty")
    if not str(event.get("venue", "")).strip():
        errors.append("venue must not be empty")
    return errors


def validate_dataset(events: list[dict], previous_count: int | None = None) -> list[str]:
    errors = []
    for index, event in enumerate(events):
        for error in validate_event(event):
            errors.append(f"event {index}: {error}")
    if previous_count and previous_count >= 20 and len(events) < previous_count * 0.5:
        errors.append(
            f"suspicious count drop: previous={previous_count}, current={len(events)}"
        )
    return errors
```

- [ ] **Step 3: Add CLI validator**

`scripts/validate_events.py` must load each supplied JSON path, call `validate_dataset`, print `[OK]`/`[FAIL]`, and return nonzero on validation failure.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_validate.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/events/validate.py scripts/validate_events.py tests/test_validate.py
git commit -m "feat: validate event datasets before writes"
```

---

### Task 5: Add Collector Types, HTTP Client, Registry Metadata, and Router

**Files:**
- Create: `scripts/collectors/__init__.py`
- Create: `scripts/collectors/base.py`
- Create: `scripts/collectors/router.py`
- Modify: `sources.json`
- Create: `tests/test_router.py`

**Interfaces:**
- `CollectorResult(events: list[dict], status: str, message: str = "")`
- `collect_source(source: dict, year: int, month: int) -> CollectorResult`

- [ ] **Step 1: Add base collector types**

```python
from dataclasses import dataclass, field
import requests

UA = "Mozilla/5.0 (compatible; SouthFloridaEventsRadar/2.0; +GitHubActions)"


@dataclass
class CollectorResult:
    events: list[dict] = field(default_factory=list)
    status: str = "ok"
    message: str = ""


class HttpClient:
    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def get(self, url: str) -> requests.Response:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response
```

- [ ] **Step 2: Add router registry validation tests**

```python
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
    }
    assert collector_name(source) == "zeyzey"
```

- [ ] **Step 3: Implement registry helpers**

```python
REQUIRED_SOURCE_KEYS = {"name", "url", "county", "default_city"}


def validate_source(source: dict) -> list[str]:
    return [
        f"missing source key: {key}"
        for key in sorted(REQUIRED_SOURCE_KEYS - set(source))
    ]


def collector_name(source: dict) -> str:
    return str(source.get("collector") or "jsonld")
```

- [ ] **Step 4: Expand every `sources.json` record**

Each record must now include:

```json
{
  "name": "ZeyZey",
  "url": "https://calendar.zeyzeymiami.com/",
  "county": "miami",
  "collector": "zeyzey",
  "default_city": "Little River",
  "browser_fallback": false
}
```

Use dedicated collector names for every major venue in the approved spec. Set `browser_fallback: true` initially for DAER/Hard Rock Nightlife, LIV, E11EVEN, Club Space, Factory Town, Kemistry, and Backyard.

- [ ] **Step 5: Test the complete registry**

Add a test that iterates through `sources.json`, calls `validate_source`, and asserts each source's `county` matches its parent county key.

- [ ] **Step 6: Commit**

```bash
git add scripts/collectors sources.json tests/test_router.py
git commit -m "refactor: add collector registry and routing metadata"
```

---

### Task 6: Move Generic JSON-LD Collection Into the New Engine

**Files:**
- Create: `scripts/collectors/jsonld.py`
- Create: `tests/test_jsonld_collector.py`

**Interfaces:**
- `parse_jsonld_html(...) -> list[dict]`
- `collect_jsonld(...) -> CollectorResult`

- [ ] **Step 1: Write fixture test**

Use `tests/fixtures/jsonld/basic_events.html` and assert:
- one event is found
- name is `September Test Concert`
- date is `2026-09-12`
- venue is `Test Arena`

- [ ] **Step 2: Implement JSON-LD parser**

Move the current `flatten_jsonld`, schema.org event detection, location/offers extraction, and month filtering into `scripts/collectors/jsonld.py`. Convert raw records through `normalize_event`.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_jsonld_collector.py tests/test_normalize.py -q
```

- [ ] **Step 4: Commit**

```bash
git add scripts/collectors/jsonld.py tests/test_jsonld_collector.py
git commit -m "refactor: move jsonld collection into collector engine"
```

---

### Task 7: Add Reusable Server-Rendered Event Card Parsing

**Files:**
- Create: `scripts/collectors/html_cards.py`
- Create: `tests/test_html_cards.py`

**Interfaces:**
- `CardSelectors`
- `parse_event_cards(...) -> list[dict]`

- [ ] **Step 1: Write a failing synthetic card test**

Test HTML:

```html
<div class="event-card">
  <a class="title" href="/events/jo-koy">Jo Koy</a>
  <div class="date">September 4, 2026</div>
  <div class="time">8:00 PM</div>
  <div class="venue">Hard Rock Live</div>
  <div class="price">Ticketed</div>
</div>
```

Assert the parser returns Jo Koy on `2026-09-04` with absolute URL.

- [ ] **Step 2: Implement `CardSelectors` and `parse_event_cards`**

The parser must accept CSS selectors for card/name/date/time/venue/city/cost/age/link, use BeautifulSoup, normalize each result, and filter by target month.

- [ ] **Step 3: Run tests and commit**

```bash
pytest tests/test_html_cards.py -q
git add scripts/collectors/html_cards.py tests/test_html_cards.py
git commit -m "feat: add reusable html event card parser"
```

---

### Task 8: Add Playwright Browser Fallback

**Files:**
- Create: `scripts/collectors/browser.py`
- Create: `tests/test_browser_collector.py`

**Interfaces:**
- `browser_enabled_for(source: dict) -> bool`
- `render_html(url: str, wait_selector: str | None = None, timeout_ms: int = 30000) -> str`

- [ ] **Step 1: Write browser configuration tests**

```python
from scripts.collectors.browser import browser_enabled_for


def test_browser_fallback_is_explicit():
    assert browser_enabled_for({"browser_fallback": True}) is True
    assert browser_enabled_for({"browser_fallback": False}) is False
    assert browser_enabled_for({}) is False
```

- [ ] **Step 2: Implement Chromium renderer**

Use `playwright.sync_api.sync_playwright`, `chromium.launch(headless=True)`, `page.goto(..., wait_until="domcontentloaded")`, optional `wait_for_selector`, and always close the browser.

- [ ] **Step 3: Verify Chromium**

```bash
python -m playwright install chromium
python -c "from scripts.collectors.browser import render_html; assert len(render_html('https://example.com')) > 100"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/collectors/browser.py tests/test_browser_collector.py
git commit -m "feat: add playwright browser fallback"
```

---

### Task 9: Add Fixture Capture Utility

**Files:**
- Create: `scripts/dev/capture_fixture.py`

**Interfaces:**
- `python scripts/dev/capture_fixture.py URL OUTPUT`
- `python scripts/dev/capture_fixture.py URL OUTPUT --browser`

- [ ] **Step 1: Implement capture utility**

It must use `requests` for normal captures and `render_html` when `--browser` is supplied, then save the public HTML snapshot under `tests/fixtures/...`.

- [ ] **Step 2: Verify**

```bash
python scripts/dev/capture_fixture.py https://example.com /tmp/example.html
test -s /tmp/example.html
```

- [ ] **Step 3: Commit**

```bash
git add scripts/dev/capture_fixture.py
git commit -m "chore: add parser fixture capture tool"
```

---

### Task 10: Implement Arena/Theater Adapter Pack

**Files:**
- Create: `scripts/collectors/arenas.py`
- Create: `tests/test_arenas.py`
- Create: `tests/fixtures/arenas/*`
- Modify: `scripts/collectors/router.py`

**Interfaces:**
- `collect_arena(source, year, month, client=None) -> CollectorResult`
- Covers: Hard Rock Hollywood, Amerant, Broward Center, Kaseya, Hard Rock Stadium, Arsht, James L. Knight Center, Miami Beach Bandshell.

- [ ] **Step 1: Capture one live fixture per source**

Use `capture_fixture.py`. Each snapshot must contain at least one September event from the audited datasets.

- [ ] **Step 2: Write source-specific fixture assertions**

Known examples to assert:
- Hard Rock Hollywood: Jo Koy / Chance the Rapper / The Strokes
- Amerant: Fall Fest / Disney On Ice
- Kaseya: Juanes / Gorillaz
- Arsht: Ilan Chester / Buena Vista Social Club
- James L. Knight Center: Asake / Orishas
- Miami Beach Bandshell: Hulvey / Viva Brazil

- [ ] **Step 3: Implement adapter dispatch**

Each source parser must:
1. try JSON-LD first;
2. use source-specific card parsing if JSON-LD is insufficient;
3. normalize to the unchanged event schema;
4. return only target-month events.

- [ ] **Step 4: Route arena names and run tests**

```bash
pytest tests/test_arenas.py tests/test_jsonld_collector.py -q
```

- [ ] **Step 5: Commit**

```bash
git add scripts/collectors/arenas.py scripts/collectors/router.py tests/test_arenas.py tests/fixtures/arenas
git commit -m "feat: add major arena and theater collectors"
```

---

### Task 11: Implement Nightlife/Dynamic Venue Adapter Pack

**Files:**
- Create: `scripts/collectors/nightlife.py`
- Create: `tests/test_nightlife.py`
- Create: `tests/fixtures/nightlife/*`
- Modify: `scripts/collectors/router.py`

**Interfaces:**
- Covers: DAER/Hard Rock Nightlife, LIV, E11EVEN, Club Space, Factory Town, ZeyZey, Kemistry, Backyard, Tin Roof.

- [ ] **Step 1: Capture rendered fixtures for dynamic sources**

Use `--browser` for LIV, E11EVEN, Club Space, Factory Town, DAER, Kemistry, Backyard. Use HTTP first for ZeyZey and Tin Roof.

- [ ] **Step 2: Write known-event assertions**

Examples:
- ZeyZey: Emmit Fenn / Tonic Walter / Kasbo
- LIV: at least one current September club event
- E11EVEN: at least one current September event
- Factory Town: one audited September event
- DAER: Galantis / KREAM / OMNOM when present in fixture

- [ ] **Step 3: Implement HTTP-first + Playwright-fallback flow**

If HTTP parsing returns zero and `browser_fallback` is true:
- render page;
- parse rendered HTML;
- on timeout return `browser_timeout`;
- on browser failure return `browser_error`;
- never raise into the runner.

- [ ] **Step 4: Run tests and commit**

```bash
pytest tests/test_nightlife.py tests/test_browser_collector.py -q
git add scripts/collectors/nightlife.py scripts/collectors/router.py tests/test_nightlife.py tests/fixtures/nightlife
git commit -m "feat: add nightlife and browser-backed collectors"
```

---

### Task 12: Implement Comedy, Small Music Venue, and Racing Adapters

**Files:**
- Create: `scripts/collectors/comedy_music.py`
- Create: `tests/test_comedy_music.py`
- Create: `tests/fixtures/comedy_music/*`
- Modify: `scripts/collectors/router.py`

**Interfaces:**
- Covers Miami Improv, Dania Improv, Revolution Live, Culture Room, Gulfstream Park.

- [ ] **Step 1: Capture fixtures**

- [ ] **Step 2: Assert audited events**

Examples:
- Miami Improv: Michael Blackson / Cedric the Entertainer / Rene Vaca / Corey Holcomb
- Dania Improv: Ryan Davis / Zoltan Kaszas
- Revolution Live: YG / Michael Franti Trio / `[overtonight]`
- Culture Room: DOMi & JD BECK / Vader
- Gulfstream: Taste at the Track

- [ ] **Step 3: Verify multiple showtimes remain separate**

Add a test that the same comedian on the same date at 7 PM and 9:30 PM creates two records.

- [ ] **Step 4: Implement adapters, run tests, commit**

```bash
pytest tests/test_comedy_music.py tests/test_merge.py -q
git add scripts/collectors/comedy_music.py scripts/collectors/router.py tests/test_comedy_music.py tests/fixtures/comedy_music
git commit -m "feat: add comedy music and racing collectors"
```

---

### Task 13: Implement Municipal/Tourism/Community Adapters

**Files:**
- Create: `scripts/collectors/municipal.py`
- Create: `tests/test_municipal.py`
- Create: `tests/fixtures/municipal/*`
- Modify: `scripts/collectors/router.py`

**Interfaces:**
- Broward: Hollywood, Sunrise, Fort Lauderdale, Visit Lauderdale.
- Miami-Dade: Miami Beach, Wynwood BID, Doral, Coral Gables, Miami Worldcenter, Frost Science.

- [ ] **Step 1: Capture fixtures**

- [ ] **Step 2: Assert known community events**

Examples:
- Hollywood: ArtsPark Movie Night / Beach Sweep
- Sunrise: Kids' Fishing Derby / Village Art Plaza Farmers Market
- Fort Lauderdale: Carter Park Jamz
- Doral: Hispanic Heritage Celebration
- Coral Gables: Park(ing) Day / International Coastal Cleanup
- Miami Worldcenter: Night Market
- Frost Science: Laser Evening

- [ ] **Step 3: Implement HTTP calendar parsers**

Prefer HTTP/server-rendered parsing. Do not use Playwright unless a fixture proves it is required.

- [ ] **Step 4: Run tests and commit**

```bash
pytest tests/test_municipal.py -q
git add scripts/collectors/municipal.py scripts/collectors/router.py tests/test_municipal.py tests/fixtures/municipal
git commit -m "feat: add municipal and community collectors"
```

---

### Task 14: Add Free Public Event-Platform Discovery

**Files:**
- Create: `scripts/collectors/platforms.py`
- Create: `tests/test_platforms.py`
- Create: `tests/fixtures/platforms/*`
- Modify: `sources.json`
- Modify: `scripts/collectors/router.py`

**Interfaces:**
- Public unauthenticated pages only: Ticketmaster, Eventbrite, DICE, Resident Advisor, Shotgun, Posh.

- [ ] **Step 1: Add county-scoped platform sources only where a stable public browse/search page exists**

Include `enabled: false` for any platform/source that immediately requires credentials, challenge solving, or blocked access.

- [ ] **Step 2: Capture fixtures for accessible platforms**

- [ ] **Step 3: Add blocked/disabled behavior test**

```python
from scripts.collectors.platforms import collect_platform


def test_disabled_platform_is_skipped():
    source = {
        "name": "Blocked Example",
        "url": "https://example.com",
        "county": "miami",
        "collector": "platform_generic",
        "default_city": "Miami",
        "enabled": False,
    }
    result = collect_platform(source, 2026, 9)
    assert result.status == "disabled"
    assert result.events == []
```

- [ ] **Step 4: Implement platform collector**

Rules:
- HTTP first.
- Playwright only when explicitly enabled.
- Return `blocked`, `disabled`, `browser_error`, or `ok`; never bypass a challenge.
- Normalize only public event data.

- [ ] **Step 5: Run tests and commit**

```bash
pytest tests/test_platforms.py -q
git add scripts/collectors/platforms.py scripts/collectors/router.py sources.json tests/test_platforms.py tests/fixtures/platforms
git commit -m "feat: add free public event platform discovery"
```

---

### Task 15: Complete Failure-Isolated Collector Router

**Files:**
- Modify: `scripts/collectors/router.py`
- Modify: `tests/test_router.py`

**Interfaces:**
- Final public API: `collect_source(source, year, month) -> CollectorResult`

- [ ] **Step 1: Add exception-isolation test**

```python
import scripts.collectors.router as router


def test_source_exception_becomes_nonfatal_result(monkeypatch):
    source = {
        "name": "Broken",
        "url": "https://example.com",
        "county": "miami",
        "collector": "jsonld",
        "default_city": "Miami",
    }

    def boom(*args, **kwargs):
        raise RuntimeError("site changed")

    monkeypatch.setattr(router, "collect_jsonld", boom)
    result = router.collect_source(source, 2026, 9)

    assert result.status == "parser_error"
    assert result.events == []
    assert "site changed" in result.message
```

- [ ] **Step 2: Implement explicit collector-name groups**

Unknown names return `config_error`. Adapter exceptions become `parser_error`.

- [ ] **Step 3: Run tests and commit**

```bash
pytest tests/test_router.py -q
git add scripts/collectors/router.py tests/test_router.py
git commit -m "feat: isolate source failures in collector router"
```

---

### Task 16: Rewrite Daily Runner as Orchestration Only

**Files:**
- Replace: `scripts/update_events.py`
- Modify: `tests/test_runner.py`

**Interfaces:**
- `update_county(county, sources, year, month, root) -> tuple[int, int, list[str]]`
- `main() -> int`

- [ ] **Step 1: Add safety tests**

Test that:
- a failed source preserves all existing events;
- a newly discovered event appends;
- warnings are returned without raising;
- final datasets are validated before write.

- [ ] **Step 2: Replace monolithic updater**

The runner must:
1. load `sources.json`;
2. load current county JSON;
3. run each source independently;
4. print `[OK]`, `[WARN]`, `[SKIP]`;
5. merge discovered events;
6. validate final dataset;
7. write only valid JSON;
8. print `[DONE] county: before -> after`.

- [ ] **Step 3: Run runner safety tests**

```bash
pytest tests/test_runner.py tests/test_merge.py tests/test_validate.py -q
```

- [ ] **Step 4: Commit**

```bash
git add scripts/update_events.py tests/test_runner.py
git commit -m "refactor: make daily updater a safe orchestrator"
```

---

### Task 17: Upgrade GitHub Actions for V2

**Files:**
- Modify: `.github/workflows/update-events.yml`

- [ ] **Step 1: Replace the workflow**

```yaml
name: Update South Florida events

on:
  schedule:
    - cron: "30 12 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-events:
    runs-on: ubuntu-latest
    timeout-minutes: 25

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright Chromium
        run: python -m playwright install --with-deps chromium

      - name: Run tests
        run: pytest -q

      - name: Update event JSON
        run: python scripts/update_events.py

      - name: Validate generated JSON
        run: python scripts/validate_events.py broward-events.json miami-events.json

      - name: Commit changes
        run: |
          git config user.name "south-florida-events-bot"
          git config user.email "actions@users.noreply.github.com"
          git add broward-events.json miami-events.json
          if git diff --cached --quiet; then
            echo "No event changes today."
          else
            git commit -m "Daily event update"
            git push
          fi
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/update-events.yml
git commit -m "ci: test and render dynamic sources daily"
```

---

### Task 18: Run V2 Against the Audited Baseline

**Files:**
- Existing: `broward-events.json`
- Existing: `miami-events.json`

- [ ] **Step 1: Confirm starting counts**

```bash
python - <<'PY'
import json
for path in ("broward-events.json", "miami-events.json"):
    data=json.load(open(path, encoding="utf-8"))
    print(path, len(data))
PY
```

Expected audited baseline:
- Broward: at least 130 records
- Miami-Dade: at least 188 records

If lower, restore the audited JSON before continuing.

- [ ] **Step 2: Run all tests**

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run updater**

```bash
python scripts/update_events.py
```

Expected: each source emits `[OK]`, `[WARN]`, or `[SKIP]`; both counties emit `[DONE]`.

- [ ] **Step 4: Validate JSON**

```bash
python scripts/validate_events.py broward-events.json miami-events.json
```

Expected: both `[OK]`.

- [ ] **Step 5: Guard audited counts**

```bash
python - <<'PY'
import json
minimums={"broward-events.json":130,"miami-events.json":188}
for path, minimum in minimums.items():
    count=len(json.load(open(path, encoding="utf-8")))
    assert count >= minimum, (path, count, minimum)
    print(path, count)
PY
```

- [ ] **Step 6: Prove schema did not change**

```bash
python - <<'PY'
import json
required={"date","time","name","venue","city","category","cost","url","source","age","featured","new"}
for path in ("broward-events.json","miami-events.json"):
    events=json.load(open(path, encoding="utf-8"))
    assert all(set(e)==required for e in events), path
print("schema unchanged")
PY
```

Expected: `schema unchanged`.

- [ ] **Step 7: Commit verified data changes only if present**

```bash
git add broward-events.json miami-events.json
git diff --cached --quiet || git commit -m "data: refresh events with updater v2"
```

---

### Task 19: Document Operations and Recovery

**Files:**
- Modify: `README-AUTO-UPDATE.md`

- [ ] **Step 1: Document daily operations**

Cover:
- Actions → Update South Florida events → Run workflow
- `[OK]`, `[WARN]`, `[SKIP]`, `[DONE]`
- how to identify a broken source parser
- how to capture a fresh fixture
- how to run tests
- how to run the updater manually
- how to validate JSON
- why a failed source never deletes events
- why a blocked platform is disabled rather than bypassed
- how to restore JSON from Git history

Include:

```bash
pip install -r requirements.txt
python -m playwright install chromium
pytest -q
python scripts/update_events.py
python scripts/validate_events.py broward-events.json miami-events.json
```

- [ ] **Step 2: Final verification**

```bash
pytest -q
python scripts/validate_events.py broward-events.json miami-events.json
```

Expected: all tests pass; both files validate.

- [ ] **Step 3: Commit**

```bash
git add README-AUTO-UPDATE.md
git commit -m "docs: document updater v2 operations"
```

---

## Final Verification Checklist

```text
[ ] pytest -q passes
[ ] Playwright Chromium installs in GitHub Actions
[ ] workflow_dispatch manual run succeeds
[ ] Broward JSON validates
[ ] Miami-Dade JSON validates
[ ] Broward does not destructively drop below the audited baseline
[ ] Miami-Dade does not destructively drop below the audited baseline
[ ] Event schema remains exactly unchanged
[ ] One intentionally broken source produces WARN but the run still succeeds
[ ] At least one JavaScript-heavy source produces events through Playwright
[ ] Multiple same-day comedy showtimes stay separate
[ ] Duplicate cross-source listings collapse correctly
[ ] No paid service or API key is required
[ ] GitHub Pages still loads both dashboards
```

## Rollout

1. Implement V2 in an isolated branch/worktree.
2. Run the complete test suite.
3. Run against copies of the audited event JSON.
4. Compare counts and spot-check newly discovered events.
5. Merge only after verification.
6. Run `workflow_dispatch` once on `main`.
7. Confirm a green Actions run.
8. Refresh both live dashboards.
9. Leave the daily schedule enabled.

If a venue changes markup later, update only that source adapter plus its fixture/test.
