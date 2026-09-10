# South Florida Events Dashboard — Sep–Dec 2026 Multi-Month Design

**Date:** 2026-09-10  
**Project:** `south-florida-events-dashboard`  
**Scope:** Miami-Dade + Broward dashboards and their daily updater

## Goal

Expand the existing September-only South Florida events dashboards so each county dashboard supports **September, October, November, and December 2026** from a single page and single county event dataset.

The existing Miami and Broward dashboard URLs remain unchanged. A month selector lets the user switch months without navigating to separate pages. The scheduled GitHub Actions updater discovers and maintains the current month plus all remaining months through December 2026.

The system remains 100% free: no paid APIs, paid scraping services, required subscriptions, or required API keys for core operation.

## Approved Product Decisions

1. Keep **one Miami-Dade dashboard** and **one Broward dashboard**.
2. Add one **month selector** with September, October, November, and December 2026.
3. Default to the **current month** when the current date is within Sep–Dec 2026.
4. If opened after December 2026, default to **December 2026** rather than an unsupported month.
5. Keep **favorites shared across all four months** for each county.
6. Preserve past-month events for browsing; do not rescrape completed months every day.
7. Scan the current month and every future month through December on each scheduled update.
8. Continue using the existing county JSON files instead of creating one JSON file per month.
9. Preserve the existing event schema.
10. A failed source or failed month must not stop the rest of the update.

## Existing Constraints and Current Behavior

The current updater calls each county collector only for `now.year` and `now.month`. The dashboards contain September-specific labels, a September-only 30-day calendar, a fixed September day offset, a hard-coded `todayDay`, and September-specific quick-filter ranges. This design removes those assumptions without changing the external event record format.

Current event schema remains:

```json
{
  "date": "",
  "time": "",
  "name": "",
  "venue": "",
  "city": "",
  "category": "",
  "cost": "",
  "url": "",
  "source": "",
  "age": "",
  "featured": false,
  "new": true
}
```

No new required event fields are introduced for the Sep–Dec expansion.

## Dashboard UX

### Month selector

Add a month control near the existing filters on both `miami.html` and `broward.html`.

Supported values:

- September 2026 (`2026-09`)
- October 2026 (`2026-10`)
- November 2026 (`2026-11`)
- December 2026 (`2026-12`)

The selector must work on desktop and mobile. Switching month:

- filters the county dataset to the selected year-month;
- clears `selectedDay`;
- rerenders the calendar with the correct weekday offset and day count;
- recalculates event count, free-event count, source count, and other selected-month stats;
- updates the calendar heading and event-list heading;
- keeps search, city, category, and price selections active;
- keeps favorites intact.

### Default month

The dashboard chooses the selected month at load time from the browser's local date:

- Sep 2026 → September
- Oct 2026 → October
- Nov 2026 → November
- Dec 2026 → December
- before Sep 2026 → September
- after Dec 2026 → December

This avoids a broken state outside the supported range.

### Calendar rendering

Calendar layout must be calculated from the selected month rather than hard-coded for September.

For each selected month, calculate:

- first weekday of the month;
- number of days in the month;
- blank leading cells;
- actual current-day highlight only when the selected month equals the current browser month/year.

Day cells continue showing up to four event previews plus a `+N more` row.

### Empty months

If a selected month has no events yet, show:

> No events found yet — check back as new events are announced.

The calendar should still render the month's dates rather than displaying a data-load error.

## Filtering Behavior

### Month scoping

Month filtering happens before normal dashboard filters. The effective pipeline is:

```text
All county events
→ selected month
→ city/category/price/search
→ quick mode
→ selected calendar day
→ sort
```

Stats and calendar counts use the same selected-month scope so totals are internally consistent.

### Search/category/price/city

Existing search, city, category, and price filters remain unchanged in behavior, but their displayed results apply to the selected month.

City/category dropdowns may be populated from the whole county dataset so switching months does not require rebuilding controls. A filter value with zero matches in a month simply returns the empty-state message.

### This week / This weekend

Replace the current hard-coded September date ranges with real date arithmetic.

Rules:

- `This week` and `This weekend` are anchored to the browser's actual current date.
- They return events only when the selected month contains those actual dates.
- If the user selects a different month from the real current month, these modes naturally return zero events rather than pretending a future month's first week is "this week."
- `All month`, `Newly added`, `Featured`, and `Favorites` remain useful for every selected month.

This preserves the literal meaning of the existing controls and removes September-specific assumptions.

## Favorites

Keep one county-specific localStorage favorites set:

- Miami key remains county-specific.
- Broward key remains county-specific.
- No month is added to the storage key.

Because the current event key contains the event date, time, name, and venue, events from different months remain distinct while still living in one shared favorites list.

Behavior:

- favoriting an October event persists when switching to December;
- switching months never clears favorites;
- `Favorites` quick mode shows favorites that belong to the selected month;
- the stored favorites collection itself remains shared across Sep–Dec.

## Updater Architecture

### Tracking window

Introduce a supported end month of **December 2026**.

Each daily run computes the month list to scan:

```text
If current date is Sep 2026: Sep, Oct, Nov, Dec
If current date is Oct 2026: Oct, Nov, Dec
If current date is Nov 2026: Nov, Dec
If current date is Dec 2026: Dec
After Dec 2026: no scheduled discovery months
```

Completed months stay in `miami-events.json` and `broward-events.json` but are not rescanned on normal daily runs.

### County/month loop

The updater should orchestrate collection by month and county while continuing to isolate source failures.

Conceptual flow:

```text
load sources.json
load existing county JSON
for each tracked month:
    for each source:
        collect_source(source, 2026, month)
        log result with county + month context
merge discoveries into the full county dataset
validate final dataset
write county JSON once
write last-updated.json
```

Writing once per county avoids repeatedly serializing the same file and allows validation to examine the complete Sep–Dec dataset before committing.

### Logging

Logs must make month-level coverage visible, for example:

```text
[OK] Miami 2026-10 / ZeyZey: 18 events
[WARN] Miami 2026-11 / Resident Advisor: blocked
[OK] Broward 2026-12 / Amerant Bank Arena: 7 events
[DONE] miami: 250 -> 338; months=2026-09,2026-10,2026-11,2026-12; warnings=2
```

A zero-event result from a source marked `warn_on_empty` remains a warning and includes the month.

### Failure isolation

The existing failure-isolation behavior remains mandatory:

- one source error does not terminate a month;
- one month's source failures do not terminate other months;
- a blocked platform is skipped/warned, never bypassed;
- empty/failed collection never deletes existing events;
- invalid final JSON is never written.

## Merge, Deduplication, and Material Changes

The existing merge layer continues to operate on one county-wide dataset across all four months.

Primary duplicate identity remains based on normalized event identity, using date/name/venue and time where required for multiple performances.

When a richer matching event is rediscovered:

- richer venue/city/category/cost/age/source/URL data may update the existing record;
- time changes update the matching event rather than create a duplicate when identity can be established confidently;
- venue/date changes should replace the prior matching record only when the source/URL or other identity evidence is strong enough to avoid merging unrelated events;
- cancellations may be represented in the visible event name/status wording while retaining the source URL, because the schema is intentionally unchanged.

The expansion must not introduce duplicates simply because the same event is collected while scanning multiple months or multiple platforms.

## Data Retention

September events remain in the county JSON after September ends. The same applies to October and November.

No automatic month purge is part of this change.

This means the files become a Sep–Dec 2026 archive while the UI selects one month at a time.

## GitHub Actions

Keep the existing scheduled GitHub Actions workflow and GitHub Pages deployment model.

The workflow still:

```text
Checkout
→ Set up Python
→ Install dependencies
→ Install Playwright Chromium
→ Run tests
→ Run multi-month updater
→ Validate county JSON
→ Commit changed JSON + timestamp
→ GitHub Pages deploy
```

No new service, secret, API key, database, or server is required.

## Files Expected to Change

Primary production files:

- `scripts/update_events.py`
- `miami.html`
- `broward.html`

Potential supporting changes if needed during implementation:

- `scripts/events/merge.py`
- `scripts/events/validate.py`
- `README-AUTO-UPDATE.md`
- `README.md`

Tests expected to change/add:

- `tests/test_runner.py`
- `tests/test_dashboard_features.py`
- tests covering dynamic month calendar behavior
- tests covering future-month preservation and scanning

The event JSON schema itself does not change.

## Testing Requirements

### Updater tests

Verify:

1. September run scans Sep–Dec.
2. October run scans Oct–Dec and preserves September data.
3. November run scans Nov–Dec and preserves Sep–Oct.
4. December run scans only December.
5. A source failure in October does not prevent November/December collection.
6. An empty future-month source does not delete existing future-month records.
7. Discoveries from multiple months merge into one county file.
8. The final county dataset validates before write.
9. `last-updated.json` is still produced once per successful run.

### Dashboard tests

Verify for both Miami and Broward:

1. Month selector exposes Sep/Oct/Nov/Dec 2026.
2. Default month follows the browser date and clamps outside the supported range.
3. October renders 31 days with the correct leading blank cells.
4. November renders 30 days correctly.
5. December renders 31 days correctly.
6. Month switching resets selected day.
7. Month switching preserves search/category/city/price values.
8. Favorites persist across month switches.
9. Favorite mode only displays favorites within the selected month.
10. Stats recalculate against the selected month.
11. Current-day highlight appears only in the selected current month.
12. Empty months show the approved friendly message.
13. Add-to-calendar continues exporting the correct event date/time across all months.
14. Existing mobile layout remains usable with the added selector.

### Regression tests

The existing collector, merge, validation, calendar-export, and workflow tests must remain green.

## Rollout

1. Implement against the current Sep. 10 dashboard code.
2. Keep the existing September event data intact.
3. Add multi-month updater tests first.
4. Implement updater tracking window and month-aware logging.
5. Add dashboard month-selector tests first.
6. Implement dynamic calendar/month filtering in Miami.
7. Mirror the same behavior in Broward.
8. Run the full test suite and JSON validation.
9. Run the updater locally for Sep–Dec and inspect event counts by month.
10. Produce the replacement repo files/ZIP for GitHub.
11. After commit, manually trigger **Update South Florida events** once.
12. Confirm the Action log shows county + month collection and GitHub Pages deploys successfully.

## Success Criteria

The upgrade is complete when:

- Miami and Broward each use one page with a Sep–Dec selector.
- The selected month controls calendar, list, stats, and filters.
- Shared favorites survive month switches.
- Calendar geometry is correct for every supported month.
- Daily updates scan the current month plus remaining 2026 months.
- Completed months remain browseable without being rescanned daily.
- Source/month failures are visible in logs but nonfatal.
- Existing event schema remains unchanged.
- No existing September event data is lost.
- Full automated tests and JSON validation pass.
- GitHub Pages continues to run with no paid dependency.
