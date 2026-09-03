# South Florida Events Updater V2

The repository updates the Broward and Miami-Dade event JSON files every morning using a free hybrid collector engine.

## What runs daily

GitHub Actions runs `.github/workflows/update-events.yml` at 12:30 UTC (8:30 AM Eastern during daylight saving time). The workflow:

1. checks out the repo;
2. installs Python dependencies;
3. installs Playwright Chromium;
4. runs the automated tests;
5. runs the event updater;
6. validates both event JSON files;
7. commits only if the JSON files changed.

## Manual run

In GitHub open **Actions → Update South Florida events → Run workflow**.

## Log meanings

- `[OK] Source: N events` — source completed normally.
- `[WARN] Source: ...` — source failed, timed out, or changed markup; the rest of the update continues.
- `[SKIP] Source: disabled` — intentionally disabled public source.
- `[DONE] broward: before -> after` / `[DONE] miami: before -> after` — county merge completed.

A failed source never deletes existing curated events. New discoveries are merged into the existing JSON files.

## Local verification

```bash
pip install -r requirements.txt
python -m playwright install chromium
python -m pytest -q
python -m scripts.update_events
python -m scripts.validate_events broward-events.json miami-events.json
```

Use `python -m pytest` rather than the standalone `pytest` command so the repository root is always on Python's import path.

## Fixing a source parser

If one source starts producing `[WARN]` or zero events while its public website clearly has events:

1. identify the source from the Actions log;
2. capture a fresh public page fixture with `scripts/dev/capture_fixture.py`;
3. update only that source's collector/parser;
4. update its fixture test;
5. run `python -m pytest -q` before committing.

Normal capture:

```bash
python scripts/dev/capture_fixture.py "PUBLIC_URL" tests/fixtures/source.html
```

JavaScript-rendered capture:

```bash
python scripts/dev/capture_fixture.py "PUBLIC_URL" tests/fixtures/source.html --browser
```

The updater does not bypass CAPTCHAs, authentication, access controls, or rate limits. Public platforms that cannot be accessed normally should remain disabled.

## Restore event data

If an event JSON file ever needs to be rolled back, open that file in GitHub, use **History**, choose the last good commit, and restore that version. The updater's merge and validation guards are designed to prevent destructive count drops before they reach the live dashboard.
