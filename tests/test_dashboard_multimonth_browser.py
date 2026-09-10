from contextlib import contextmanager
import json
from pathlib import Path
import shutil

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


def render_test_html(filename: str, events: list[dict]) -> str:
    html = (ROOT / filename).read_text(encoding="utf-8")
    calendar_js = (ROOT / "calendar.js").read_text(encoding="utf-8")
    months_js = (ROOT / "dashboard-months.js").read_text(encoding="utf-8")
    html = html.replace('<script src="calendar.js"></script>', f"<script>{calendar_js}</script>")
    html = html.replace('<script src="dashboard-months.js"></script>', f"<script>{months_js}</script>")
    fetch_stub = f"""<script>
window.fetch = async function(url) {{
  const value = String(url || '');
  if (value.includes('last-updated.json')) {{
    return {{ok:true, status:200, json: async () => ({{updated_at:'2026-09-10T09:00:00-04:00'}})}};
  }}
  return {{ok:true, status:200, json: async () => ({json.dumps(events)})}};
}};
</script>"""
    html = html.replace("<script>\nlet events=[];", fetch_stub + "\n<script>\nlet events=[];", 1)
    return html


@contextmanager
def dashboard_page(filename: str, events: list[dict]):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=shutil.which("chromium") or None)
        page = browser.new_page()
        page.set_content(render_test_html(filename, events), wait_until="load")
        page.wait_for_selector("#cal [data-d]")
        try:
            yield page
        finally:
            browser.close()


def test_miami_switching_month_resets_day_but_keeps_search_and_filters():
    with dashboard_page("miami.html", TEST_EVENTS) as page:
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


def test_miami_favorite_persists_across_month_switches():
    with dashboard_page("miami.html", TEST_EVENTS) as page:
        page.select_option("#month", "2026-10")
        page.locator(".fav-btn").click()
        assert page.locator(".fav-btn").inner_text() == "★"

        page.select_option("#month", "2026-09")
        page.select_option("#month", "2026-10")
        assert page.locator(".fav-btn").inner_text() == "★"

        page.locator('[data-mode="favorites"].chip').click()
        assert "October Test" in page.locator("#list").inner_text()


def test_miami_empty_supported_month_uses_friendly_message_and_renders_dates():
    with dashboard_page("miami.html", TEST_EVENTS) as page:
        page.select_option("#month", "2026-12")
        assert page.locator("#cal [data-d]").count() == 31
        assert page.locator("#list").inner_text() == (
            "No events found yet — check back as new events are announced."
        )


def test_broward_switches_to_november_with_dynamic_30_day_calendar():
    broward_events = [
        dict(TEST_EVENTS[0], date="2026-09-12", name="Broward September", city="Fort Lauderdale"),
        dict(TEST_EVENTS[1], date="2026-11-21", name="Broward November", city="Hollywood"),
    ]
    with dashboard_page("broward.html", broward_events) as page:
        page.select_option("#month", "2026-11")
        assert page.locator("#monthHeading").inner_text() == "November 2026"
        assert page.locator("#cal [data-d]").count() == 30
        assert "Broward November" in page.locator("#list").inner_text()
        assert "Broward September" not in page.locator("#list").inner_text()
