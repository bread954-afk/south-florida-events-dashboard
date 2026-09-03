from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CALENDAR_JS = ROOT / "calendar.js"


def run_node(expression: str) -> str:
    script = f"""
const cal = require({json.dumps(str(CALENDAR_JS))});
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
    return completed.stdout


def test_calendar_script_exists_and_is_loaded_by_both_dashboards():
    assert CALENDAR_JS.exists()
    for filename in ("broward.html", "miami.html"):
        html = (ROOT / filename).read_text(encoding="utf-8")
        assert '<script src="calendar.js"></script>' in html
        assert 'class="calendar-btn"' in html
        assert 'SFCalendar.downloadEvent(event)' in html


def test_timed_event_generates_timed_ics():
    expression = """cal.buildIcs({
      date:'2026-09-12', time:'8:00 PM', name:'Test Concert',
      venue:'Test Arena', city:'Miami', url:'https://example.com/event'
    })"""
    ics = json.loads(run_node(expression))
    assert "BEGIN:VEVENT" in ics
    assert "DTSTART:20260912T200000" in ics
    assert "DTEND:20260912T220000" in ics
    assert "SUMMARY:Test Concert" in ics
    assert "LOCATION:Test Arena\\, Miami" in ics
    assert "URL:https://example.com/event" in ics


def test_tbd_event_generates_all_day_ics():
    expression = """cal.buildIcs({
      date:'2026-09-20', time:'TBD', name:'TBD Event',
      venue:'Venue', city:'Sunrise', url:'https://example.com/tbd'
    })"""
    ics = json.loads(run_node(expression))
    assert "DTSTART;VALUE=DATE:20260920" in ics
    assert "DTEND;VALUE=DATE:20260921" in ics
    assert "DTSTART:20260920T" not in ics


def test_calendar_filename_is_sanitized():
    filename = json.loads(run_node("cal.calendarFilename({name:'TLC & Salt-N-Pepa!'})"))
    assert filename == "TLC-Salt-N-Pepa.ics"
