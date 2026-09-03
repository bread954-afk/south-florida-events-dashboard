# Automatic event updater

This adds a free GitHub Actions job that runs every morning and scans the configured event-source pages for schema.org Event data.

Files to add to the repository:
- `.github/workflows/update-events.yml`
- `scripts/update_events.py`
- `sources.json`
- `requirements.txt`

Important:
- No API key or password is required.
- The workflow has write access only to the repository where you install it.
- It updates only `broward-events.json` and `miami-events.json`.
- Some event websites render entirely with JavaScript or block automated requests, so this no-key updater will not discover every event that a broad web search can find. Your ChatGPT daily watches can still catch those gaps.
